import os
import abc
import signal
import itertools
import Queue # Queue.Empty
import multiprocessing

class WorkerPool(object):
    '''
    A pool of worker processes, somewhat similar to multiprocessing.Pool, but
    more suitable for data generated lazily or in an event-driven manner, and
    adopting a MapReduce-like working model.

    A WorkerPool consists of multiprocessing.cpu_count() processes, one of
    which being the receiver (which is similar to a reducer), and the others
    being workers (which are analogous to mappers). The receiver and the
    workers must conform to the Receiver and Worker interfaces defined by this
    module, which consist of the setup(), work()/receive() and done() methods.

    The setup() method will get called right after forking, but before any tasks
    are sent to the workers and receiver. Likewise, the done() method will get
    called when there are no more tasks to be processed, as signaled by the
    application by calling WorkerPool.done(), first in all the workers, then in
    the receiver when all worker processes have finished.

    Before WorkerPool.done() is called, the work() method in workers will get
    called with whatever object is passed to WorkerPool.post(), and its return
    value is passed to the receiver's receive() method. This model makes
    WorkerPool suitable for large datasets that are generated lazily or via
    event-driven libraries.

    A WorkerPool can also be canceled with the cancel() method. This will cause
    SIGTERM to be sent to all child processes, which will intercept it, call
    their respective Worker/Receiver's done() method, and exit gracefully.
    Behavior is undefined if any other methods are called on a WorkerPool after
    cancel(), or if cancel() is invoked more than once.

    For example, here's how WorkerPool can be used to process a big XML file
    such that the parent process parses it, the workers process the data it
    contains, and the receiver saves the results to a database, and the file is
    never entirely loaded in memory:

        import xml.etree.ElementTree as ET

        class DataParser(workerpool.Worker):
            def setup():
                pass

            def work(data):
                result = self.do_stuff_with_data(data)
                return result

            def done():
                pass
            ...

        class DataWriter(workerpool.Receiver):
            def setup():
                self.db = self.connect_to_database()

            def receive(result):
                self.write_to_database(db, result)

            def done():
                pass
            ...

        wp = WorkerPool(DataParser(), DataWriter())
        iterparser = ET.iterparse(large_xml_file)
        for _, element in iterparser:
            data = element.find('data').text
            wp.post(data)
            element.clear()
        wp.done()
    '''

    def __init__(self, worker, receiver):
        self._procs = []
        self._queues = []
        self._canceled = False

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

    def cancel(self):
        for p in self._procs:
            os.kill(p.pid, signal.SIGTERM)
        for p in self._procs:
            p.join()

    def _sigterm_handler(self, sig, stack):
        self._canceled = True

    def _loop_common(self, q, on_task):
        signal.signal(signal.SIGTERM, self._sigterm_handler)
        while not self._canceled:
            try:
                msg, task = q.get(timeout = 1)
            except Queue.Empty:
                continue
            if msg == 'DONE':
                break
            if not self._canceled:
                on_task(task)

    def _worker_loop(self, worker, q):
        def on_task(task):
            result = worker.work(task)
            self._queues[0].put(('TASK', result))
        worker.setup()
        self._loop_common(q, on_task)
        worker.done()

    def _receiver_loop(self, receiver):
        def on_task(task):
            receiver.receive(task)
        receiver.setup()
        self._loop_common(self._queues[0], on_task)
        receiver.done()

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
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def setup(self):
        pass

    @abc.abstractmethod
    def receive(self, result):
        pass

    @abc.abstractmethod
    def done(self):
        pass

