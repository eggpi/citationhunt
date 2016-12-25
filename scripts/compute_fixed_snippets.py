#!/usr/bin/env python

'''
Compute some statistics on how many snippets have been fixed across databases.

Usage:
    compute_fixed_snippets.py <lang-code>

Use 'global' for lang-code to go over all languages.
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

def load_pages_and_snippets_to_process(cursor, lang_code, start_date, end_date):
    cursor.execute('''
        SELECT ts, snippet_id, url FROM requests
        WHERE url LIKE "%%redirect%%" AND
        ts BETWEEN %s AND %s AND lang_code = %s
        AND snippet_id NOT IN (
            SELECT snippet_id FROM fixed WHERE
            clicked_ts BETWEEN %s AND %s AND lang_code = %s
        ) ORDER BY ts''', (start_date, end_date, lang_code) * 2)

    # url is of the form /<lang_code>/redirect?id=<snippet_id>&to=wiki/<page>,
    # so we can parse the page and snippet id out of it. The snippet id is also
    # in the database as a separate column, but get it from the url anyway.
    page_title_to_snippets = {}
    for ts, _, url in cursor:
        query_dict = urlparse.parse_qs(urlparse.urlparse(url).query)
        if not 'id' in query_dict or not 'to' in query_dict:
            log.info('malformed redirect url: %r' % url)
            continue

        snippet_id = query_dict['id'][0]
        page_title = query_dict['to'][0]
        if not page_title.startswith('wiki/'):
            log.info('malformed redirect url: %r' % url)
            continue
        page_title = page_title.split('/', 1)[1]

        page_title_to_snippets.setdefault(page_title, {})[snippet_id] = ts
    return page_title_to_snippets

def compute_fixed_snippets(cfg):
    log.info('computing fixed snippets for %s' % cfg.lang_code)

    live_db = chdb.init_db(cfg.lang_code)
    stats_db = chdb.init_stats_db()

    # Load snippets that have been clicked in the past few hours
    to_ts = datetime.datetime.today()
    from_ts = to_ts - datetime.timedelta(hours = 3)
    page_title_to_snippets = stats_db.execute_with_retry(
        load_pages_and_snippets_to_process, cfg.lang_code, from_ts, to_ts)

    if not page_title_to_snippets:
        log.info('No pages to process!')
        return
    log.info('Will reparse pages: %r' % page_title_to_snippets.keys())

    # Now fetch and parse the pages and check which snippets are gone
    wiki = wikitools.wiki.Wiki(
            'https://' + cfg.wikipedia_domain + '/w/api.php')
    wiki.setUserAgent(
            'citationhunt (https://tools.wmflabs.org/citationhunt)')
    parser = snippet_parser.create_snippet_parser(wiki, cfg)

    for page_title, snippet_to_ts in page_title_to_snippets.items():
        page = wikitools.Page(wiki, page_title)
        snippets = parser.extract(page.getWikiText())
        # FIXME Duplicated logic with parse_live.py :(
        for sec, snips in snippets:
            for sni in snips:
                id = mkid(d(page.title) + sni)
                snippet_to_ts.pop(id, None)

        for snippet_id, clicked_ts in snippet_to_ts.items():
            log.info(snippet_id)
            stats_db.execute_with_retry_s(
                'INSERT IGNORE INTO fixed VALUES (%s, %s, %s)',
                clicked_ts, snippet_id, cfg.lang_code)

    live_db.close()
    stats_db.close()
    return 0

if __name__ == '__main__':
    start = time.time()
    args = docopt.docopt(__doc__)
    lang_codes = (
        config.LANG_CODES_TO_LANG_NAMES.keys()
        if args['<lang-code>'] == 'global'
        else [args['<lang-code>']])

    for lang_code in lang_codes:
        cfg = config.get_localized_config(lang_code)
        compute_fixed_snippets(cfg)
    log.info('all done in %d seconds.' % (time.time() - start))
