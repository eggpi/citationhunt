#!/usr/bin/env python

from __future__ import unicode_literals

import chdb
import snippet_parser

import mwparserfromhell

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import abc
import sys
import pickle
import sqlite3
import hashlib
import itertools
import multiprocessing

WIKIPEDIA_BASE_URL = 'https://en.wikipedia.org'
WIKIPEDIA_WIKI_URL = WIKIPEDIA_BASE_URL + '/wiki/'

NAMESPACE_ARTICLE = '0'
NAMESPACE_CATEGORY = '14'

def e(s):
    if type(s) == str:
        return str
    return s.encode('utf-8')

def d(s):
    if type(s) == unicode:
        return s
    return unicode(s, 'utf-8')

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
        for q in self._queues:
            q.put(('DONE', None))
        for p in self._procs:
            p.join()

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

class RowParser(Worker):
    def setup(self):
        pass

    def work(self, task):
        rows = []
        kind, info = task
        if kind == 'category':
            # nothing to parse, and info is a single row
            return (kind, [info])

        pageid, title, wikitext = info
        url = WIKIPEDIA_WIKI_URL + title

        snippets = snippet_parser.extract_snippets(wikitext)
        for s in snippets:
            id = hashlib.sha1(e(title + s)).hexdigest()[:2*8]
            row = (id, s, url, title)
            rows.append(row)
        return (kind, rows)

    def done(self):
        pass

# sqlite3 sucks at multiprocessing, so we confine all database access to a
# single process
class DatabaseWriter(Receiver):
    def __init__(self):
        self.db = None

    def setup(self):
        self.db = chdb.init_db()

    def receive(self, task):
        kind, rows = task
        if kind == 'category':
            self.write_category_rows(rows)
        else:
            self.write_article_rows(rows)

    def write_article_rows(self, rows):
        with self.db:
            for row in rows:
                try:
                    self.db.execute('''
                        INSERT INTO cn VALUES(?, ?, ?, ?)''', row)
                except sqlite3.IntegrityError as err:
                    print err
                    print row

    def write_category_rows(self, rows):
        with self.db:
            for row in rows:
                self.db.execute('''
                    INSERT INTO cat VALUES(?, ?)''', row)

    def done(self):
        self.db.close()

def handle_category(wp, element):
    id = d(element.find('id').text)
    if element.find('redirect') is not None:
        return

    title = d(element.find('title').text)
    wp.post(('category', (id, title)))
    return

def handle_article(wp, element, pageids, stats):
    # elements are not pickelable, so we can't pass them to workers. extract
    # all the relevant information here and offload only the wikicode
    # parsing.

    id = d(element.find('id').text)
    if id not in pageids:
        return
    pageids.remove(id)

    if element.find('redirect') is not None:
        stats['redirect'].append(id)
        return

    title = d(element.find('title').text)
    text = element.find('revision/text').text
    if text is None:
        stats['empty'].append(id)
        return
    text = d(text)

    wp.post(('article', (id, title, text)))
    return

def parse_xml_dump(pages_articles_xml, pageids):
    count = 0
    stats = {'redirect': [], 'empty': [], 'pageids': None}

    parser = RowParser()
    writer = DatabaseWriter()
    wp = WorkerPool(parser, writer)
    iterparser = ET.iterparse(pages_articles_xml)
    for _, element in iterparser:
        element.tag = element.tag[element.tag.rfind('}')+1:]
        if element.tag == 'page':
            ns = element.find('ns').text
            if ns == NAMESPACE_ARTICLE:
                handle_article(wp, element, pageids, stats)
            elif ns == NAMESPACE_CATEGORY:
                handle_category(wp, element)
            count += 1
            if count % 10 == 0:
                print >>sys.stderr, '\rprocessed about %d pages' % count,
            element.clear()
    wp.done()
    stats['pageids'] = pageids
    print >>sys.stderr

    if len(pageids) > 0:
        print >>sys.stderr, '%d pageids were not found' % len(stats['pageids'])
    print >>sys.stderr, '%d pages were redirects' % len(stats['redirect'])
    print >>sys.stderr, '%d pages were empty' % len(stats['empty'])
    with open('stats.pickle', 'wb') as statsf:
        pickle.dump(stats, statsf)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print >>sys.stderr, \
            'usage: %s <pages-articles.xml> <pageid file>' % sys.argv[0]
        sys.exit(1)
    xml_dump_filename = sys.argv[1]
    pageids_file = sys.argv[2]
    with open(pageids_file) as pf:
        pageids = set(itertools.imap(str.strip, pf))
    parse_xml_dump(xml_dump_filename, pageids)
