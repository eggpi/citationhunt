#!/usr/bin/env python

'''
Parser for the pages+articles XML dump for CitationHunt.

Given a file with one pageid per line, this script will find unsourced
snippets in the pages in the pageid file. It will store the pages containing
valid snippets in the `articles` database table, and the snippets in the
`snippets` table.

This script will also fill a `categories` table in the Wikipedia database
linking category pageids to titles. This is a subset of the `pages` table in the
Wikipedia dump.

Usage:
    parse_pages_articles.py <pages-articles-xml> <pageid-file>
'''

from __future__ import unicode_literals

import sys
sys.path.append('../')

import chdb
import snippet_parser
import workerpool
from utils import *

import docopt
import mwparserfromhell

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import pickle
import sqlite3
import pymysql
import itertools

WIKIPEDIA_BASE_URL = 'https://en.wikipedia.org'
WIKIPEDIA_WIKI_URL = WIKIPEDIA_BASE_URL + '/wiki/'

NAMESPACE_ARTICLE = '0'
NAMESPACE_CATEGORY = '14'

CITATION_NEEDED_HTML = '<span class="citation-needed">[citation needed]</span>'

class RowParser(workerpool.Worker):
    def setup(self):
        pass

    def work(self, task):
        kind, info = task
        if kind == 'category':
            # nothing to parse, and info is a single row
            return (kind, [info])

        pageid, title, wikitext = info
        url = WIKIPEDIA_WIKI_URL + title.replace(' ', '_')

        snippets_rows = []
        snippets = snippet_parser.extract_snippets(wikitext)
        for sec, snips in snippets:
            sec = sec.replace(' ', '_')
            for sni in snips:
                sni = sni.replace(snippet_parser.MARKER, CITATION_NEEDED_HTML)
                id = mkid(title + sni)
                row = (id, sni, sec, pageid)
                snippets_rows.append(row)

        if snippets_rows:
            article_row = (pageid, url, title, "unassigned")
            return (kind, {'article': article_row, 'snippets': snippets_rows})
        return (kind, {})

    def done(self):
        pass

# sqlite3 sucks at multiprocessing, so we confine all database access to a
# single process
class DatabaseWriter(workerpool.Receiver):
    def __init__(self):
        self.chdb = None
        self.wpdb = None

    def setup(self):
        self.chdb = chdb.reset_db()

        self.wpdb = pymysql.connect(
            user = 'root', database = 'wikipedia', charset = 'utf8')
        self.wpcursor = self.wpdb.cursor()
        self.wpcursor.execute('''DROP TABLE IF EXISTS categories''')
        self.wpcursor.execute('''
            CREATE TABLE categories (page_id INT PRIMARY KEY, title VARCHAR(255))
        ''')

    def receive(self, task):
        kind, rows = task
        if kind == 'category':
            self.write_category_rows(rows)
        else:
            self.write_article_rows(rows)

    def write_article_rows(self, rows):
        if not rows:
            return

        with self.chdb:
            self.chdb.execute('''
                INSERT INTO articles VALUES(?, ?, ?, ?)''', rows['article'])
            self.chdb.executemany('''
                INSERT OR IGNORE INTO snippets VALUES(?, ?, ?, ?)''',
                rows['snippets'])

    def write_category_rows(self, rows):
        with self.wpdb:
            self.wpcursor.executemany('''
                INSERT INTO categories VALUES(%s, %s)''', rows)

    def done(self):
        self.chdb.close()
        self.wpdb.close()

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
