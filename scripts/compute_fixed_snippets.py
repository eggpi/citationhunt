#!/usr/bin/env python

'''
Compute some statistics on how many snippets have been fixed across databases.

Usage:
    compute_fixed_snippets.py
'''

from __future__ import unicode_literals

import os
import sys
_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)
import time
import urlparse
import datetime

import config
import chdb
from utils import *
import snippet_parser

import docopt
import wikitools

log = Logger()

def load_snippet_clicks_between(cursor, lang_code, start_date, end_date):
    cursor.execute(
        'SELECT ts, referrer FROM requests WHERE url LIKE "%%redirect%%" AND '
        'ts BETWEEN %s AND %s AND lang_code = %s AND referrer IS NOT NULL '
        'ORDER BY ts',
        (start_date, end_date, lang_code))

    clicked_snippets = {}
    for ts, url in cursor:
        query_dict = urlparse.parse_qs(urlparse.urlparse(url).query)
        if 'id' in query_dict:
            clicked_snippets[query_dict['id'][0]] = ts
    return clicked_snippets

def compute_fixed_snippets(cfg):
    log.info('computing fixed snippets for %s' % cfg.lang_code)

    live_db = chdb.init_db(cfg.lang_code)
    stats_db = chdb.init_stats_db()

    # Load snippets that have been clicked in the past few hours
    to_ts = datetime.datetime.today()
    from_ts = to_ts - datetime.timedelta(hours = 3)
    clicked = stats_db.execute_with_retry(
        load_snippet_clicks_between, cfg.lang_code, from_ts, to_ts)

    # Don't re-process snippets we've already looked at
    already_seen = stats_db.execute_with_retry_s(
        'SELECT snippet_id FROM fixed WHERE '
        'clicked_ts BETWEEN %s AND %s AND lang_code = %s',
        from_ts, to_ts, lang_code) or []
    for id in already_seen:
        clicked.pop(id, None)

    # Partition the snippets by page, loading each page once
    wiki = None  # lazy loaded
    pages_to_process = {}  # page_id -> (page, {snippet_id: clicked_ts})
    for snippet_id, clicked_ts in clicked.iteritems():
        page_id = live_db.execute_with_retry_s(
            'SELECT article_id FROM snippets WHERE id = %s',
            (snippet_id,))
        if page_id is None:
            log.info("Didn't find snippet %s in the database!" % snippet_id)
            continue
        page_id = page_id[0][0]  # one row, one column

        log.info('will reparse page %s' % page_id)
        if page_id not in pages_to_process:
            if wiki is None:
                wiki = wikitools.wiki.Wiki(
                    'https://' + cfg.wikipedia_domain + '/w/api.php')
                wiki.setUserAgent(
                    'citationhunt (https://tools.wmflabs.org/citationhunt)')
            pages_to_process[page_id] = (
                wikitools.Page(wiki, pageid = page_id), {})
        pages_to_process[page_id][1][snippet_id] = clicked_ts

    if not pages_to_process:
        log.info('No pages to process!')
        return

    # Now parse the pages and check which snippets are gone
    parser = snippet_parser.create_snippet_parser(wiki, cfg)
    for page, target_snippets in pages_to_process.values():
        snippets = parser.extract(page.getWikiText())
        for sec, snips in snippets:
            for sni in snips:
                id = mkid(d(page.title) + sni)
                target_snippets.pop(id, None)

        for snippet_id, clicked_ts in target_snippets.items():
            log.info(snippet_id)
            stats_db.execute_with_retry_s(
                'INSERT INTO fixed VALUES (%s, %s, %s)',
                clicked_ts, snippet_id, cfg.lang_code)

    live_db.close()
    stats_db.close()
    return 0

if __name__ == '__main__':
    start = time.time()
    args = docopt.docopt(__doc__)
    for lang_code in config.lang_code_to_config:
        cfg = config.get_localized_config(lang_code)
        compute_fixed_snippets(cfg)
    log.info('all done in %d seconds.' % (time.time() - start))
