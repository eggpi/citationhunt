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

import config
import chdb
from utils import *

import docopt

log = Logger()

def load_snippets(cursor):
    cursor.execute('SELECT id FROM snippets')
    return set(row[0] for row in cursor)

def load_table_creation_date(cursor, table):
    cursor.execute(
        'SELECT create_time FROM information_schema.tables '
        'WHERE table_schema = DATABASE() AND table_name = %s', (table,))
    return cursor.fetchone()[0]

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

def compute_fixed_snippets():
    start = time.time()
    # FIXME This could probably just be one query on a single database
    # connection, insead of one connection per database and loading all
    # snippets in memory for comparison.
    cfg = config.get_localized_config()
    scratch_db = chdb.init_scratch_db()
    live_db = chdb.init_db(cfg.lang_code)
    stats_db = chdb.init_stats_db()

    # Find the set of snippets that that were "clicked" (redirected to article)
    # between the dates of the previous/live and next/scratch database
    from_ts = live_db.execute_with_retry(load_table_creation_date, 'snippets')
    to_ts = scratch_db.execute_with_retry(load_table_creation_date, 'snippets')
    clicked = stats_db.execute_with_retry(
        load_snippet_clicks_between, cfg.lang_code, from_ts, to_ts)

    # Load the snippets from both databases
    scratch_snippets = scratch_db.execute_with_retry(load_snippets)
    live_snippets = live_db.execute_with_retry(load_snippets)

    # And for each snippet that disappeared across databases AND had been
    # clicked in the meantime, store its information in the stats database.
    gone = live_snippets.difference(scratch_snippets)
    for id, clicked_ts in clicked.iteritems():
        if id in gone:
            log.info(id)
            stats_db.execute_with_retry_s(
                'INSERT INTO fixed VALUES (%s, %s, %s)',
                clicked_ts, id, cfg.lang_code)

    log.info('all done in %d seconds.' % (time.time() - start))
    scratch_db.close()
    live_db.close()
    stats_db.close()
    return 0

if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    sys.exit(compute_fixed_snippets())
