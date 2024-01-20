import flask

import chdb
import utils
from .common import *

import datetime
import os
import json
import re
import itertools

crawler_user_agents_regexps = [
    re.compile(obj['pattern'], re.IGNORECASE)
    for obj in json.load(
        open(os.path.join(os.path.dirname(__file__),
            'crawler-user-agents', 'crawler-user-agents.json')))
]

referrer_spam_regexps = [
    re.compile(domain.strip(), re.IGNORECASE)
    for domain in open(
        os.path.join(os.path.dirname(__file__),
            'referrer-spam-blacklist', 'spammers.txt'))
]

def is_spam(user_agent, referrer):
    # Normalize None to the empty string
    user_agent = user_agent or ''
    referrer = referrer or ''
    return any(itertools.chain(
        (r.search(user_agent) for r in crawler_user_agents_regexps),
        (r.search(referrer) for r in referrer_spam_regexps)))

def log_request(response):
    user_agent = flask.request.headers.get('User-Agent', None)
    referrer = flask.request.referrer or None
    if is_spam(user_agent, referrer):
        return response
    lang_code = getattr(flask.g, '_lang_code', None)
    if lang_code not in config.LANG_CODES_TO_LANG_NAMES:
        lang_code = None
    id = flask.request.args.get('id')
    cat = flask.request.args.get('cat')
    inter_id = flask.request.args.get('custom')
    url = flask.request.url
    prefetch = (flask.request.headers.get('purpose') == 'prefetch' or
                flask.request.headers.get('X-Moz') == 'prefetch')
    status_code = response.status_code

    with get_stats_db().cursor() as cursor, chdb.ignore_warnings():
        cursor.execute('INSERT INTO requests VALUES '
            '(NOW(), %s, %s, %s, %s, %s, %s, %s, %s)',
            (lang_code, id, cat, url, prefetch, status_code, referrer,
             inter_id))
    return response

def pad(data, days, default = 0):
    """
    Given an iterable of (datestr, value) extending up to `days`
    in the past, pad it with entries containing the `default` value
    so it actually spans all days between now and `days` ago.
    """
    return sorted(dict(
        [((datetime.datetime.now() -
            datetime.timedelta(days=d)).strftime('%Y-%m-%d'), default)
        for d in range(days)] + list(data)).items())

@validate_lang_code
def stats(lang_code):
    graphs = [] # title, data table as array, type
    stats_cursor = get_stats_db().cursor()

    try:
        days = int(flask.request.args.get('days', 10))
    except:
        days = 10
    inter_id = flask.request.args.get('custom', None)

    # Choose a convenient view for the queries below, creating temporary ones
    # if needed for the intersection requested. In the intersection case, we
    # hash the inter_id again because we need to unsafely use it the CREATE VIEW
    # statement, but we haven't validated it and don't trust it.

    inter_view_id = utils.mkid(inter_id) if inter_id is not None else None
    requests_view = 'requests_' + lang_code
    fixed_view = 'fixed_' + lang_code
    if inter_view_id is not None:
        requests_view = 'requests_' + inter_view_id
        fixed_view = 'fixed_' + inter_view_id
        stats_cursor.execute(
            'CREATE OR REPLACE VIEW ' + requests_view + ' AS '
            'SELECT * FROM requests WHERE inter_id = %s',
            (inter_id,))
        stats_cursor.execute(
            'CREATE OR REPLACE VIEW ' + fixed_view + ' AS '
            'SELECT * FROM fixed WHERE inter_id = %s',
            (inter_id,))

    stats_cursor.execute(
        'SELECT DATE_FORMAT(clicked_ts, GET_FORMAT(DATE, "ISO")) dt, COUNT(*) '
        'FROM ' + fixed_view + ' '
        'WHERE DATEDIFF(NOW(), clicked_ts) < %s GROUP BY dt ORDER BY dt',
        (days,))
    graphs.append((
        'Number of snippets fixed in the past %s days (estimate!)' % days,
        json.dumps(
            [['Date', lang_code]] + pad(stats_cursor, days)), 'line'))

    stats_cursor.execute(
        'SELECT DATE_FORMAT(ts, GET_FORMAT(DATE, "ISO")) dt, COUNT(*) '
        'FROM ' + requests_view + ' '
        'WHERE snippet_id IS NOT NULL AND status_code = 200 '
        'AND DATEDIFF(NOW(), ts) < %s GROUP BY dt ORDER BY dt', (days,))
    graphs.append((
        'Number of snippets served in the past %s days' % days,
        json.dumps([['Date', lang_code]] + pad(stats_cursor, days)), 'line'))

    stats_cursor.execute(
        'SELECT DATE_FORMAT(ts, GET_FORMAT(DATE, "ISO")) AS dt, COUNT(*) '
        'FROM ' + requests_view +  ' '
        'WHERE url LIKE "%%redirect%%" AND status_code = 302 '
        'AND DATEDIFF(NOW(), ts) < %s GROUP BY dt ORDER BY dt', (days,))
    graphs.append((
        'Number of redirects to article in the past %s days' % days,
        json.dumps([['Date', lang_code]] + pad(stats_cursor, days)), 'line'))

    # FIXME don't assume tools labs?
    stats_cursor.execute(
        'SELECT referrer, COUNT(*) FROM ' + requests_view + ' '
        'WHERE status_code = 200 AND DATEDIFF(NOW(), ts) < %s '
        'AND referrer NOT LIKE "%%tools.wmflabs.org/citationhunt%%" '
        'AND referrer NOT LIKE "%%citationhunt.toolforge.org%%" '
        'AND referrer IS NOT NULL '
        'GROUP BY referrer ORDER BY COUNT(*) DESC LIMIT 30', (days,))
    graphs.append((
        '30 most popular referrers in the past %s days' % days,
        json.dumps([['Referrer', 'Count']] + list(stats_cursor)), 'table'))

    data_rows = []
    stats_cursor.execute(
        'SELECT category_id, COUNT(*) FROM ' + requests_view + ' '
        'WHERE snippet_id IS NOT NULL AND category_id IS NOT NULL AND '
        'category_id != "all" AND status_code = 200 '
        'AND DATEDIFF(NOW(), ts) < %s GROUP BY category_id '
        'ORDER BY COUNT(*) DESC LIMIT 30', (days,))
    ch_cursor = get_db(lang_code).cursor()
    for category_id, count in stats_cursor:
        ch_cursor.execute(
            'SELECT title FROM categories WHERE id = %s', (category_id,))
        title = list(ch_cursor)[0][0] if ch_cursor.rowcount else "(gone)"
        data_rows.append((title, count))
    graphs.append((
        '30 most popular categories in the past %s days' % days,
        json.dumps([['Category', 'Count']] + data_rows), 'table'))

    if inter_view_id is not None:
        stats_cursor.execute('DROP VIEW IF EXISTS ' + requests_view)
        stats_cursor.execute('DROP VIEW IF EXISTS ' + fixed_view)
    return flask.render_template('stats.html', graphs = graphs)
