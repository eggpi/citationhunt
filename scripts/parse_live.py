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
import yamwapi as mwapi
import snippet_parser
from utils import *

import docopt
import requests

import cProfile
import functools
import glob
import itertools
import multiprocessing
import pstats
import re
import shutil
import tempfile
import time
import traceback
import urllib
import cPickle as pickle

cfg = config.get_localized_config()
WIKIPEDIA_BASE_URL = 'https://' + cfg.wikipedia_domain
WIKIPEDIA_WIKI_URL = WIKIPEDIA_BASE_URL + '/wiki/'
WIKIPEDIA_API_URL = WIKIPEDIA_BASE_URL + '/w/api.php'

MAX_EXCEPTIONS_PER_SUBPROCESS = 5

DATA_TRUNCATED_WARNING_RE = re.compile(
    'Data truncated for column .* at row (\d+)')

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

def query_pageids(wiki, pageids):
    params = {
        'pageids': '|'.join(map(str, pageids)),
        'prop': 'revisions',
        'rvprop': 'content'
    }
    for response in self.wiki.query(params):
        for id, page in response['query']['pages'].items():
            if 'title' not in page:
                continue
            title = d(page['title'])
            text = page['revisions'][0]['*']
            if not text:
                continue
            text = d(text)
            yield (id, title, text)

# In py3: types.SimpleNamespace
class State(object):
    pass
self = State() # Per-process state

def initializer(backdir):
    self.backdir = backdir

    self.wiki = mwapi.MediaWikiAPI(WIKIPEDIA_API_URL, cfg.user_agent)
    self.parser = snippet_parser.create_snippet_parser(self.wiki, cfg)
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
    stats_path = os.path.join(self.backdir, 'stats-%s' % os.getpid())
    with open(stats_path, 'wb') as stats_f:
        pickle.dump(self.parser.stats, stats_f)

def with_max_exceptions(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwds):
        try:
            return fn(*args, **kwds)
        except:
            traceback.print_exc()
            self.exception_count += 1
            if self.exception_count > MAX_EXCEPTIONS_PER_SUBPROCESS:
                log.info('Too many exceptions, quitting!')
                raise
    return wrapper

@with_max_exceptions
def work(pageids):
    rows = []
    results = query_pageids(self.wiki, pageids)
    for pageid, title, wikitext in results:
        url = WIKIPEDIA_WIKI_URL + title.replace(' ', '_')

        snippets_rows = []
        snippets = self.parser.extract(wikitext)
        for sec, snips in snippets:
            sec = section_name_to_anchor(sec)
            for sni in snips:
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

        # We can't allow data to be truncated for HTML snippets, as that can
        # completely break the UI, so we detect truncation warnings and get rid
        # of the corresponding data.
        warnings = cursor.execute('SHOW WARNINGS')
        truncated_snippets = []
        for _, _, message in cursor.fetchall():
            m = DATA_TRUNCATED_WARNING_RE.match(message)
            if m is None:
                # Not a truncation, ignore (it's already logged)
                continue
            # MySQL warnings index rows starting at 1
            idx = int(m.groups()[0]) - 1
            truncated_snippets.append((r['snippets'][idx][0],))
        if len(truncated_snippets) < len(r['snippets']):
            cursor.executemany('''
                DELETE FROM snippets WHERE id = %s''', truncated_snippets)
        else:
            # Every single snippet was truncated, remove the article itself
            cursor.execute('''DELETE FROM articles WHERE page_id = %s''',
                (r['article'][0],))
    for r in rows:
        self.chdb.execute_with_retry(insert, r)

def parse_live(pageids, timeout):
    backdir = tempfile.mkdtemp(prefix = 'citationhunt_parse_live_')
    pool = multiprocessing.Pool(
        # The number of processes per CPU is pretty much made up. The processes
        # are I/O bound as most of the time is spent querying the Wikipedia API.
        processes = multiprocessing.cpu_count() * 8,
        initializer = initializer, initargs = (backdir,))

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

    parser_stats = snippet_parser.stats.merge_stats(
        pickle.load(file(stats_file))
        for stats_file in glob.glob(os.path.join(backdir, 'stats-*')))
    lengths = parser_stats.snippet_lengths
    log.info('percentiles for snippet lengths:')
    log.info('50th: %d' % snippet_parser.stats.percentile(lengths, 50))
    log.info('70th: %d' % snippet_parser.stats.percentile(lengths, 70))
    log.info('90th: %d' % snippet_parser.stats.percentile(lengths, 90))
    log.info('95th: %d' % snippet_parser.stats.percentile(lengths, 95))

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
