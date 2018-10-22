import errno
import itertools as it
import os
import sys
import hashlib

def e(s):
    if type(s) == str:
        return s
    return s.encode('utf-8')

def d(s):
    if type(s) == unicode:
        return s
    return unicode(s, 'utf-8')

def mkid(s):
    return hashlib.sha1(e(s)).hexdigest()[:2*4]

def running_in_virtualenv():
    return hasattr(sys, 'real_prefix')

def running_in_tools_labs():
    return os.path.exists('/etc/wmflabs-project')

# Thanks, StackOverflow! https://stackoverflow.com/questions/600268
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

class Logger(object):
    def __init__(self):
        self._mode = 'INFO'

    def progress(self, message):
        message = e(message)
        if not sys.stderr.isatty():
            return

        if self._mode == 'PROGRESS':
            print >>sys.stderr, '\r',
        print >>sys.stderr, message,
        self._mode = 'PROGRESS'

    def info(self, message):
        message = e(message)
        if self._mode == 'PROGRESS':
            print >>sys.stderr

        print >>sys.stderr, message
        self._mode = 'INFO'

def pair_with_next(iterator):
    """
    Given an iterator (..., x, y, z, w, ...), returns another iterator of
    tuples that pair each element to its successor, that is
    (..., (x, y), (y, z), (z, w), ...).

    The iterator "wraps around" at the end, that is, the last element is
    paired with the first.
    """

    i1, i2 = it.tee(iterator)
    return it.izip(i1, it.chain(i2, [next(i2)]))

def ichunk(iterable, chunk_size):
    it0 = iter(iterable)
    while True:
        it1, it2 = it.tee(it.islice(it0, chunk_size))
        next(it2)  # raises StopIteration if it0 is exhausted
        yield it1
