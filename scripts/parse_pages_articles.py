#!/usr/bin/env python

'''
Parser for the pages+articles XML dump for CitationHunt.

Given a file with one pageid per line, this script will find unsourced
snippets in the pages in the pageid file. It will store the pages containing
valid snippets in the `articles` database table, and the snippets in the
`snippets` table.

Usage:
    parse_pages_articles.py <pages-articles-xml.bz2> <pageid-file>
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

import bz2file
import pickle
import sqlite3
import itertools
import urllib

WIKIPEDIA_BASE_URL = 'https://en.wikipedia.org'
WIKIPEDIA_WIKI_URL = WIKIPEDIA_BASE_URL + '/wiki/'

NAMESPACE_ARTICLE = '0'

CITATION_NEEDED_HTML = '<span class="citation-needed">[citation needed]</span>'

log = Logger()

def section_name_to_anchor(section):
    # See Sanitizer::escapeId
    # https://doc.wikimedia.org/mediawiki-core/master/php/html/classSanitizer.html#ae091dfff62f13c9c1e0d2e503b0cab49
    section = section.replace(' ', '_')
    section = urllib.quote(e(section))
    section = section.replace('%3A', ':')
    section = section.replace('%', '.')
    return section

def insert_citation_needed_html(snippet):
    return snippet.replace(snippet_parser.MARKER, CITATION_NEEDED_HTML)

class RowParser(workerpool.Worker):
    def setup(self):
        pass

    def work(self, task):
        kind, info = task
        assert kind == 'article'

        pageid, title, wikitext = info
        url = WIKIPEDIA_WIKI_URL + title.replace(' ', '_')

        snippets_rows = []
        snippets = snippet_parser.extract_snippets(wikitext)
        for sec, snips in snippets:
            sec = section_name_to_anchor(sec)
            for sni in snips:
                sni = insert_citation_needed_html(sni)
                id = mkid(title + sni)
                row = (id, sni, sec, pageid)
                snippets_rows.append(row)

        if snippets_rows:
            article_row = (pageid, url, title, 'unassigned')
            return (kind, {'article': article_row, 'snippets': snippets_rows})
        return (kind, {})

    def done(self):
        pass

# sqlite3 sucks at multiprocessing, so we confine all database access to a
# single process
class DatabaseWriter(workerpool.Receiver):
    def __init__(self):
        self.chdb = None

    def setup(self):
        self.chdb = chdb.reset_db()

    def receive(self, task):
        kind, rows = task
        assert kind == 'article'
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

    def done(self):
        self.chdb.close()

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

def parse_xml_dump(pages_articles_xml_bz2, pageids):
    count = 0
    stats = {'redirect': [], 'empty': [], 'pageids': None}

    parser = RowParser()
    writer = DatabaseWriter()
    wp = workerpool.WorkerPool(parser, writer)
    iterparser = ET.iterparse(bz2file.BZ2File(pages_articles_xml_bz2))
    for _, element in iterparser:
        element.tag = element.tag[element.tag.rfind('}')+1:]
        if element.tag == 'page':
            ns = element.find('ns').text
            if ns == NAMESPACE_ARTICLE:
                handle_article(wp, element, pageids, stats)
            count += 1
            if count % 10 == 0:
                log.progress('processed about %d pages' % count)
            element.clear()
    wp.done()
    stats['pageids'] = pageids

    if len(pageids) > 0:
        log.info('%d pageids were not found' % len(stats['pageids']))
    log.info('%d pages were redirects' % len(stats['redirect']))
    log.info('%d pages were empty' % len(stats['empty']))
    with open('stats.pkl', 'wb') as statsf:
        pickle.dump(stats, statsf)

if __name__ == '__main__':
    arguments = docopt.docopt(__doc__)
    xml_dump_filename = arguments['<pages-articles-xml.bz2>']
    pageids_file = arguments['<pageid-file>']
    with open(pageids_file) as pf:
        pageids = set(itertools.imap(str.strip, pf))
    parse_xml_dump(xml_dump_filename, pageids)
