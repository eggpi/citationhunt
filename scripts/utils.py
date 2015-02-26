import hashlib

def e(s):
    if type(s) == str:
        return str
    return s.encode('utf-8')

def d(s):
    if type(s) == unicode:
        return s
    return unicode(s, 'utf-8')

def mkid(s):
    return hashlib.sha1(e(s)).hexdigest()[:2*4]
