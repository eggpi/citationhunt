#!/usr/bin/env python

'''
Parser for the pages+articles XML dump for CitationHunt.

Given a file with open pageid per line, this script will find unsourced
snippets in the pages in the pageid file and store them to a
'citationhunt.sqlite3' database. It will also discover the names and page ids
of all category pages and store them in the database.

Usage:
    parse_pages_articles.py <pages-articles-xml> <pageid-file>
'''

from __future__ import unicode_literals

import chdb
import snippet_parser
import workerpool

import docopt
import mwparserfromhell

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import sys
import pickle
import sqlite3
import hashlib
import itertools

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

class RowParser(workerpool.Worker):
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
class DatabaseWriter(workerpool.Receiver):
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
    wp = workerpool.WorkerPool(parser, writer)
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
    with open('stats.pkl', 'wb') as statsf:
        pickle.dump(stats, statsf)

if __name__ == '__main__':
    arguments = docopt.docopt(__doc__)
    xml_dump_filename = arguments['<pages-articles-xml>']
    pageids_file = arguments['<pageid-file>']
    with open(pageids_file) as pf:
        pageids = set(itertools.imap(str.strip, pf))
    parse_xml_dump(xml_dump_filename, pageids)
