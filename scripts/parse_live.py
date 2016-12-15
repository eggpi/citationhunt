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
_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)

import chdb
import config
import snippet_parser
import multiprocessing
from utils import *

import docopt
import requests
import wikitools

import StringIO
import cProfile
import functools
import glob
import itertools
import pstats
import shutil
import tempfile
import time
import traceback
import urllib

cfg = config.get_localized_config()
WIKIPEDIA_BASE_URL = 'https://' + cfg.wikipedia_domain
WIKIPEDIA_WIKI_URL = WIKIPEDIA_BASE_URL + '/wiki/'
WIKIPEDIA_API_URL = WIKIPEDIA_BASE_URL + '/w/api.php'

MAX_EXCEPTIONS_PER_SUBPROCESS = 5

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

# FIXME: This is here because it reuses the Wikipedia API session, but maybe
# it belongs in the snippet_parser?
def to_html(wiki, opener, text):
    params = {
        'action': 'parse',
        'format': 'json',
        'text': text
    }
    request = wikitools.APIRequest(wiki, params)
    request.opener = opener
    # FIXME Sometimes the request fails because the text is too long;
    # in that case, the API response is HTML, not JSON, which raises
    # an exception when wikitools tries to parse it.
    #
    # Normally this would cause wikitools to happily retry forever
    # (https://github.com/alexz-enwp/wikitools/blob/b71481796c350/wikitools/api.py#L304),
    # which is a bug, but due to our use of a custom opener, wikitools'
    # handling of the exception raises its own exception: the object returned
    # by our opener doesnt support seek().
    #
    # We use that interesting coincidence to catch the exception and move
    # on, bypassing wikitools' faulty retry, but this is obviously a terrible
    # "solution".
    try:
        ret = request.query()['parse']['text']['*']
    except:
        return ''

    # Links are always relative so they end up broken in the UI. We could make
    # them absolute, but let's just remove them (by replacing with <span>) since
    # we don't actually need them.
    import xml.etree.cElementTree as ET
    ret = '<div>' + ret + '</div>'
    tree = ET.fromstring(e(ret))
    for parent_of_a in tree.findall('.//a/..'):
        for i, tag in enumerate(parent_of_a):
            if tag.tag == 'a' and tag.text:
                repl = ET.Element('span')
                repl.extend(list(tag))
                if tag.text:
                    repl.text = tag.text
                if tag.tail:
                    repl.tail = tag.tail + ' '
                else:
                    repl.tail = ' '
                parent_of_a.insert(i+1, repl)
                parent_of_a.remove(tag)
    return d(ET.tostring(tree))

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

# In py3: types.SimpleNamespace
class State(object):
    pass
self = State() # Per-process state

def initializer(parser, backdir):
    self.parser = parser
    self.backdir = backdir
    self.wiki = wikitools.wiki.Wiki(WIKIPEDIA_API_URL)
    self.wiki.setUserAgent(
        'citationhunt (https://tools.wmflabs.org/citationhunt)')
    self.opener = WikitoolsRequestsAdapter()
    self.chdb = chdb.init_scratch_db()
    self.exception_count = 0

    if cfg.profile:
        self.profiler = cProfile.Profile()
        self.profiler.enable()
        # Undocumented :( https://stackoverflow.com/questions/24717468
        multiprocessing.util.Finalize(None, finalizer, exitpriority=16)

def finalizer():
    self.profiler.disable()
    profile_path = os.path.join(self.backdir, 'profile-%s' % os.getpid())
    pstats.Stats(self.profiler).dump_stats(profile_path)

def with_max_exceptions(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwds):
        try:
            return fn(*args, **kwds)
        except:
            traceback.print_exc()
            self.exception_count += 1
            if self.exception_count > MAX_EXCEPTIONS_PER_SUBPROCESS:
                raise
    return wrapper

@with_max_exceptions
def work(pageids):
    rows = []
    results = query_pageids(self.wiki, self.opener, pageids)
    for pageid, title, wikitext in results:
        url = WIKIPEDIA_WIKI_URL + title.replace(' ', '_')

        snippets_rows = []
        if cfg.html_snippet:
            snippets = self.parser.extract_sections(wikitext)
        else:
            snippets = self.parser.extract_snippets(
                wikitext, cfg.snippet_min_size, cfg.snippet_max_size)
        for sec, snips in snippets:
            sec = section_name_to_anchor(sec)
            for sni in snips:
                if cfg.html_snippet:
                    sni = to_html(self.wiki, self.opener, sni)
                    if not (cfg.snippet_min_size < len(sni) < cfg.snippet_max_size):
                        continue
                id = mkid(title + sni)
                row = (id, sni, sec, pageid)
                snippets_rows.append(row)

        if snippets_rows:
            article_row = (pageid, url, title)
            rows.append({'article': article_row, 'snippets': snippets_rows})

    def insert(cursor, r):
        cursor.execute('''
            INSERT INTO articles VALUES(%s, %s, %s)''', r['article'])
        cursor.executemany('''
            INSERT IGNORE INTO snippets VALUES(%s, %s, %s, %s)''',
            r['snippets'])
    for r in rows:
        self.chdb.execute_with_retry(insert, r)

def parse_live(pageids, timeout):
    chdb.reset_scratch_db()
    backdir = tempfile.mkdtemp(prefix = 'citationhunt_parse_live_')
    parser = snippet_parser.create_snippet_parser(cfg)
    pool = multiprocessing.Pool(
        initializer = initializer, initargs = (parser, backdir))

    # Make sure we query the API 32 pageids at a time
    tasks = []
    batch_size = 32
    pageids_list = list(pageids)
    for i in range(0, len(pageids), batch_size):
        tasks.append(pageids_list[i:i+batch_size])

    result = pool.map_async(work, tasks)
    pool.close()

    result.wait(timeout)
    if not result.ready():
        log.info('timeout, canceling the process pool!')
        pool.terminate()
    pool.join()
    try:
        result.get()
        ret = 0
    except Exception:
        log.info('Too many exceptions, failed!')
        ret = 1

    if cfg.profile:
        profiles = map(pstats.Stats,
            glob.glob(os.path.join(backdir, 'profile-*')))
        stats = reduce(
            lambda stats, other: (stats.add(other), stats)[1],
            profiles if profiles else [None])
        if stats is not None:
            stats.sort_stats('cumulative').print_stats(30)

    shutil.rmtree(backdir)
    return ret

if __name__ == '__main__':
    arguments = docopt.docopt(__doc__)
    pageids_file = arguments['<pageid-file>']
    timeout = float(arguments['--timeout'])
    start = time.time()
    with open(pageids_file) as pf:
        pageids = set(itertools.imap(str.strip, pf))
    ret = parse_live(pageids, timeout)
    log.info('all done in %d seconds.' % (time.time() - start))
    sys.exit(ret)
