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
