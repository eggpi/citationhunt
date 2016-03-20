#!/usr/bin/env python

'''
Parser for articles retrieved from the Wikipedia API for CitationHunt.

Given a file with one pageid per line, this script will find unsourced
snippets in the pages in the pageid file. It will store the pages containing
valid snippets in the `articles` database table, and the snippets in the
`snippets` table.

Usage:
    parse_live.py <pageid-file> [--timeout=<n>]

Options:
    --timeout=<n>    Maximum time in seconds to run for [default: inf].
'''

from __future__ import unicode_literals

import os
import sys
sys.path.append('../')

import chdb
import config
import snippet_parser
import workerpool
from utils import *

import docopt
import requests
import wikitools

import time
import itertools
import urllib
import StringIO

cfg = config.get_localized_config()
WIKIPEDIA_BASE_URL = 'https://' + cfg.wikipedia_domain
WIKIPEDIA_WIKI_URL = WIKIPEDIA_BASE_URL + '/wiki/'
WIKIPEDIA_API_URL = WIKIPEDIA_BASE_URL + '/w/api.php'

log = Logger()

def section_name_to_anchor(section):
    # See Sanitizer::escapeId
    # https://doc.wikimedia.org/mediawiki-core/master/php/html/classSanitizer.html#ae091dfff62f13c9c1e0d2e503b0cab49
    section = section.replace(' ', '_')
    # urllib.quote interacts really weirdly with unicode in Python2:
    # https://bugs.python.org/issue23885
    section = urllib.quote(e(section), safe = e(''))
    section = section.replace('%3A', ':')
    section = section.replace('%', '.')
    return section

def query_pageids(wiki, opener, pageids):
    params = {
        'action': 'query',
        'pageids': '|'.join(map(str, pageids)),
        'prop': 'revisions',
        'rvprop': 'content'
    }

    request = wikitools.APIRequest(wiki, params)
    request.opener = opener
    for response in request.queryGen():
        for id, page in response['query']['pages'].items():
            if 'title' not in page:
                continue
            title = d(page['title'])

            text = page['revisions'][0]['*']
            if not text:
                continue
            text = d(text)
            yield (id, title, text)

# An adapter that lets us use requests for wikitools until it doesn't grow
# native support. This allows us to have persistent connections.
class WikitoolsRequestsAdapter(object):
    def __init__(self):
        self.session = requests.Session()

    def open(self, request):
        headers = dict(request.headers)
        headers.pop('Content-length') # Let requests compute this
        response = self.session.get(
            request.get_full_url() + '?' + request.get_data(),
            headers = headers)
        return urllib.addinfourl(
            StringIO.StringIO(response.text), request.headers,
            request.get_full_url(), response.status_code)

class RowParser(workerpool.Worker):
    def setup(self):
        self.parser = snippet_parser.get_localized_snippet_parser()
        self.wiki = wikitools.wiki.Wiki(WIKIPEDIA_API_URL)
        self.wiki.setUserAgent(
            'citationhunt (https://tools.wmflabs.org/citationhunt)')
        self.opener = WikitoolsRequestsAdapter()

    def work(self, pageids):
        data = []
        results = query_pageids(self.wiki, self.opener, pageids)
        for pageid, title, wikitext in results:
            url = WIKIPEDIA_WIKI_URL + title.replace(' ', '_')

            snippets_rows = []
            snippets = self.parser.extract_snippets(
                wikitext, cfg.snippet_min_size, cfg.snippet_max_size)
            for sec, snips in snippets:
                sec = section_name_to_anchor(sec)
                for sni in snips:
                    id = mkid(title + sni)
                    row = (id, sni, sec, pageid)
                    snippets_rows.append(row)

            if snippets_rows:
                article_row = (pageid, url, title)
                data.append({'article': article_row, 'snippets': snippets_rows})
        return data

    def done(self):
        pass

# FIXME originally we needed only a single process writing to the database,
# because sqlite3 sucks at multiprocessing. We can probably change that with
# MySQL.
class DatabaseWriter(workerpool.Receiver):
    def __init__(self):
        self.chdb = None

    def setup(self):
        self.chdb = chdb.reset_scratch_db()

    def receive(self, rows):
        self.write_article_rows(rows)

    def write_article_rows(self, rows):
        if not rows:
            return

        def insert(cursor, r):
            cursor.execute('''
                INSERT INTO articles VALUES(%s, %s, %s)''', r['article'])
            cursor.executemany('''
                INSERT IGNORE INTO snippets VALUES(%s, %s, %s, %s)''',
                r['snippets'])
        for r in rows:
            self.chdb.execute_with_retry(insert, r)

    def done(self):
        self.chdb.close()

def parse_live(pageids, timeout):
    start = time.time()
    parser = RowParser()
    writer = DatabaseWriter()
    wp = workerpool.WorkerPool(parser, writer)

    batch_size = 32
    pageids_list = list(pageids)
    for i in range(0, len(pageids), batch_size):
        wp.post(pageids_list[i:i+batch_size])

    wp.join(timeout)
    if time.time() - start > timeout:
        log.info('timeout, canceling the worker pool!')
        wp.cancel()

if __name__ == '__main__':
    arguments = docopt.docopt(__doc__)
    pageids_file = arguments['<pageid-file>']
    timeout = float(arguments['--timeout'])
    with open(pageids_file) as pf:
        pageids = set(itertools.imap(str.strip, pf))
    parse_live(pageids, timeout)
    log.info('all done.')
