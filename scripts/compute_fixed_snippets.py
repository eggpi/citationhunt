#!/usr/bin/env python3

'''
Compute some statistics on how many snippets have been fixed across databases.

Usage:
    compute_fixed_snippets.py <lang-code>

Use 'global' for lang-code to go over all languages.
'''

import os
import sys
_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)
import collections
import time
import urllib.parse
import datetime
import dateutil.parser
import dateutil.tz
import logging.handlers

import config
import chdb
from utils import *
import yamwapi as mwapi
import snippet_parser

import docopt

logger = logging.getLogger('compute_fixed_snippets')
setup_logger_to_logfile(logger, 'compute_fixed_snippets.log')

# A snippet for which the user clicked through to go to Wikipedia, and
# potentially fixed once there.
ClickedSnippet = collections.namedtuple('ClickedSnippet',
    ('snippet_id', 'ts', 'inter_id'))

def datetime_naive_local_to_naive_utc(d):
    # Given a naive datetime object, assume it represents local time,
    # convert it to UTC, and return another naive datetime. We need
    # this because our database gives naive datetimes in local time, but
    # the MW API expects UTC.
    return d.replace(tzinfo = dateutil.tz.tzlocal()).astimezone(
        dateutil.tz.tzutc()).replace(tzinfo = None)

def datetime_utc_to_naive_local(d):
    # We would have liked to assert that:
    #   assert d.tzinfo == dateutil.tz.tzutc()
    # but a bug in dateutil makes it actually use tzlocal even when there's
    # an explicit 'Z' suffiz in the timestamp string, as is the case for the
    # MW API. So this is actually a UTC date, with tzinfo = tzlocal.
    # https://github.com/dateutil/dateutil/issues/349
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
        for p in list(response['query']['pages'].values()):
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
        SELECT ts, snippet_id, url, inter_id FROM requests
        WHERE url LIKE "%%redirect%%" AND
        ts BETWEEN %s AND %s AND lang_code = %s
        AND snippet_id NOT IN (
            SELECT snippet_id FROM fixed WHERE
            clicked_ts BETWEEN %s AND %s AND lang_code = %s
        ) ORDER BY ts''', (start_date, end_date, lang_code) * 2)

    # url is of the form:
    # /<lang_code>/redirect?id=<snippet_id>&custom=[<inter_id>]&to=wiki/<page>
    page_title_to_snippets = {}
    for ts, _, url, inter_id in cursor:
        query_dict = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if not 'id' in query_dict or not 'to' in query_dict:
            logger.info('malformed redirect url: %r' % url)
            continue

        snippet_id = query_dict['id'][0]
        page_title = query_dict['to'][0]
        if not page_title.startswith('wiki/'):
            logger.info('malformed redirect url: %r' % url)
            continue
        page_title = page_title.split('/', 1)[1].replace('_', ' ')
        page_title_to_snippets.setdefault(page_title, []).append(
            ClickedSnippet(snippet_id, ts, inter_id))
    return page_title_to_snippets

def compute_fixed_snippets(cfg):
    logger.info('computing fixed snippets for %s' % cfg.lang_code)

    live_db = chdb.init_db(cfg.lang_code)
    stats_db = chdb.init_stats_db()

    # Load snippets that have been clicked in the past few hours
    to_ts = datetime.datetime.today()
    from_ts = to_ts - datetime.timedelta(hours = 3)
    page_title_to_snippets = stats_db.execute_with_retry(
        load_pages_and_snippets_to_process, cfg.lang_code, from_ts, to_ts)

    if not page_title_to_snippets:
        logger.info('No pages to process!')
        return
    logger.info('Will reparse pages: %r' % list(page_title_to_snippets.keys()))

    # Now fetch and parse the pages and check which snippets are gone
    wiki = mwapi.MediaWikiAPI(
        'https://' + cfg.wikipedia_domain + '/w/api.php', cfg.user_agent)
    parser = snippet_parser.create_snippet_parser(wiki, cfg)

    for page_title, clicked_snippets in page_title_to_snippets.items():
        start_ts = min(cs.ts for cs in clicked_snippets)
        revisions = get_page_revisions(wiki, page_title, start_ts)
        for rev in revisions:
            snippets = parser.extract(rev['contents'])
            gone_in_this_revision = {
                cs.snippet_id: cs for cs in clicked_snippets}
            # FIXME Duplicated logic with parse_live.py :(
            for sec, snips in snippets:
                for sni in snips:
                    id = mkid(d(page_title) + sni)
                    gone_in_this_revision.pop(id, None)
            for snippet_id, clicked_snippet in gone_in_this_revision.items():
                if clicked_snippet.ts < rev['timestamp']:
                    logger.info('%s fixed at revision %s' % (
                        snippet_id, rev['rev_id']))
                    clicked_snippets.remove(clicked_snippet)
                    stats_db.execute_with_retry_s(
                        'INSERT IGNORE INTO fixed VALUES (%s, %s, %s, %s, %s)',
                        clicked_snippet.ts, clicked_snippet.snippet_id,
                        cfg.lang_code, rev['rev_id'], clicked_snippet.inter_id)

    live_db.close()
    stats_db.close()
    return 0

if __name__ == '__main__':
    while True:
        start = time.time()
        args = docopt.docopt(__doc__)
        lang_codes = (
            list(config.LANG_CODES_TO_LANG_NAMES.keys())
            if args['<lang-code>'] == 'global'
            else [args['<lang-code>']])

        for lang_code in lang_codes:
            cfg = config.get_localized_config(lang_code)
            if cfg.extract == 'snippet':
                compute_fixed_snippets(cfg)
        logger.info('all done in %d seconds.' % (time.time() - start))
        time.sleep(5 * 60)
