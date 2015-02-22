import abc
import itertools
import multiprocessing

# FIXME this can possibly be replaced with a simple multiprocessing.Pool()
# by turning parse_xml_dump into a generator and feeding it in parts to the
# queue using the lazy iteration trick [1]. But I didn't know that trick when
# I wrote this, and it was fun to write anyway.
# 1- https://stackoverflow.com/questions/5318936/python-multiprocessing-pool-lazy-iteration
class WorkerPool(object):
    def __init__(self, worker, receiver):
        self._procs = []
        self._queues = []

        # receiver process and queue
        self._queues.append(multiprocessing.Queue())
        self._procs.append(
            multiprocessing.Process(
                target = self._receiver_loop, args = (receiver,)))
        self._procs[0].start()

        # worker processes and queues
        nprocs = multiprocessing.cpu_count() - 1
        for _ in range(nprocs):
            q = multiprocessing.Queue()
            self._queues.append(q)
            p = multiprocessing.Process(
                target = self._worker_loop, args = (worker, q))
            p.start()
            self._procs.append(p)
        self._cycle_worker_queues = itertools.cycle(self._queues[1:])

    def post(self, obj):
        q = next(self._cycle_worker_queues)
        q.put(('TASK', obj))

    def done(self):
        # stop workers
        for q in self._queues[1:]:
            q.put(('DONE', None))
        for p in self._procs[1:]:
            p.join()

        self._queues[0].put(('DONE', None))
        self._procs[0].join()

    def _worker_loop(self, worker, q):
        worker.setup()
        while True:
            msg, task = q.get()
            if msg == 'DONE':
                worker.done()
                return
            result = worker.work(task)
            self._queues[0].put(('TASK', result))

    def _receiver_loop(self, receiver):
        receiver.setup()
        while True:
            msg, result = self._queues[0].get()
            if msg == 'DONE':
                receiver.done()
                return
            receiver.receive(result)

class Worker(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def setup(self):
        pass

    @abc.abstractmethod
    def work(self, task):
        pass

    @abc.abstractmethod
    def done(self):
        pass

class Receiver(object):
    @abc.abstractmethod
    def setup(self):
        pass

    @abc.abstractmethod
    def receive(self, result):
        pass

    @abc.abstractmethod
    def done(self):
        pass

