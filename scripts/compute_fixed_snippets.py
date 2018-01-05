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
import dateutil.parser
import dateutil.tz

import config
import chdb
from utils import *
import yamwapi as mwapi
import snippet_parser

import docopt

log = Logger()

def datetime_naive_local_to_naive_utc(d):
    # Given a naive datetime object, assume it represents local time,
    # convert it to UTC, and return another naive datetime. We need
    # this because our database gives naive datetimes in local time, but
    # the MW API expects UTC.
    return d.replace(tzinfo = dateutil.tz.tzlocal()).astimezone(
        dateutil.tz.tzutc()).replace(tzinfo = None)

def datetime_utc_to_naive_local(d):
    assert d.tzinfo == dateutil.tz.tzutc()
    return d.astimezone(dateutil.tz.tzlocal()).replace(tzinfo = None)

def get_page_revisions(wiki, title, start):
    params = {
        'prop': 'revisions',
        'rvprop': 'content|timestamp|ids',
        'rvstart': datetime_naive_local_to_naive_utc(start).isoformat(),
        'rvdir': 'newer',
        'titles': title
    }
    revisions = []  # oldest to newest
    for response in wiki.query(params):
        for p in response['query']['pages'].values():
            for r in p.get('revisions', []):
                revisions.append({
                    'rev_id': r['revid'],
                    'timestamp': datetime_utc_to_naive_local(
                        dateutil.parser.parse(r['timestamp'])),
                    'contents': r['*'],
                })
    return revisions

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
        page_title = page_title.split('/', 1)[1].replace('_', ' ')
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
    wiki = mwapi.MediaWikiAPI(
        'https://' + cfg.wikipedia_domain + '/w/api.php', cfg.user_agent)
    parser = snippet_parser.create_snippet_parser(wiki, cfg)

    for page_title, snippet_to_ts in page_title_to_snippets.items():
        start_ts = min(snippet_to_ts.values())
        revisions = get_page_revisions(wiki, page_title, start_ts)
        for rev in revisions:
            snippets = parser.extract(rev['contents'])
            gone_in_this_revision = dict(snippet_to_ts)
            # FIXME Duplicated logic with parse_live.py :(
            for sec, snips in snippets:
                for sni in snips:
                    id = mkid(d(page_title) + sni)
                    gone_in_this_revision.pop(id, None)
            for snippet_id, clicked_ts in gone_in_this_revision.items():
                if clicked_ts < rev['timestamp']:
                    log.info('%s fixed at revision %s' % (
                        snippet_id, rev['rev_id']))
                    del snippet_to_ts[snippet_id]
                    stats_db.execute_with_retry_s(
                        'INSERT IGNORE INTO fixed VALUES (%s, %s, %s, %s)',
                        clicked_ts, snippet_id, cfg.lang_code, rev['rev_id'])

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
        if cfg.extract == 'snippet':
            compute_fixed_snippets(cfg)
    log.info('all done in %d seconds.' % (time.time() - start))
