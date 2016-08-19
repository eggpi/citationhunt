import flask

import chdb
import config
from common import *

import os
import json
import re
import itertools

crawler_user_agents_regexps = [
    re.compile(obj['pattern'], re.IGNORECASE)
    for obj in json.load(
        file(os.path.join(os.path.dirname(__file__),
            'crawler-user-agents', 'crawler-user-agents.json')))
]

referrer_spam_regexps = [
    re.compile(domain.decode('utf-8').strip(), re.IGNORECASE)
    for domain in file(
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
        return
    lang_code = getattr(flask.request, 'lang_code', None)
    id = flask.request.args.get('id')
    cat = flask.request.args.get('cat')
    url = flask.request.url
    prefetch = (flask.request.headers.get('purpose') == 'prefetch' or
                flask.request.headers.get('X-Moz') == 'prefetch')
    status_code = response.status_code

    with get_stats_db() as cursor, chdb.ignore_warnings():
        cursor.execute('INSERT INTO requests VALUES '
            '(NOW(), %s, %s, %s, %s, %s, %s, %s, %s)',
            (lang_code, id, cat, url, prefetch, user_agent,
             status_code, referrer))
    return response

@validate_lang_code
def stats(lang_code):
    days = flask.request.args.get('days', 10)
    graphs = [] # title, data table as array, type
    stats_cursor = get_stats_db().cursor()
    ch_cursor = get_db(lang_code).cursor()

    stats_cursor.execute('''
        SELECT DATE_FORMAT(ts, GET_FORMAT(DATE, 'ISO')) AS dt, COUNT(*)
        FROM requests_''' + lang_code +
        ''' WHERE snippet_id IS NOT NULL AND status_code = 200
        AND DATEDIFF(NOW(), ts) < %s GROUP BY dt ORDER BY dt''', (days,))
    graphs.append((
        'Number of snippets served in the past %s days' % days,
        json.dumps([['Date', lang_code]] + list(stats_cursor)), 'line'))

    stats_cursor.execute('''
        SELECT DATE_FORMAT(ts, GET_FORMAT(DATE, 'ISO')) AS dt,
        COUNT(DISTINCT user_agent) FROM requests_''' + lang_code + '''
        WHERE snippet_id IS NOT NULL AND status_code = 200 AND
        user_agent IS NOT NULL AND DATEDIFF(NOW(), ts) < %s
        GROUP BY dt ORDER BY dt''', (days,))
    graphs.append((
        'Distinct user agents in the past %s days' % days,
        json.dumps([['Date', lang_code]] + list(stats_cursor)), 'line'))

    stats_cursor.execute('''
        SELECT DATE_FORMAT(ts, GET_FORMAT(DATE, 'ISO')) AS dt, COUNT(*)
        FROM requests_''' + lang_code +
        ''' WHERE url LIKE '%%redirect%%' AND status_code = 302
        AND DATEDIFF(NOW(), ts) < %s GROUP BY dt ORDER BY dt''', (days,))
    graphs.append((
        'Number of redirects to article in the past %s days' % days,
        json.dumps([['Date', lang_code]] + list(stats_cursor)), 'line'))

    # FIXME don't assume tools labs?
    stats_cursor.execute('''
        SELECT referrer, COUNT(*) FROM requests_''' + lang_code + '''
        WHERE status_code = 200 AND DATEDIFF(NOW(), ts) < %s
        AND referrer NOT LIKE "%%tools.wmflabs.org/citationhunt%%"
        AND referrer IS NOT NULL
        GROUP BY referrer ORDER BY COUNT(*) DESC LIMIT 30
    ''', (days,))
    graphs.append((
        '30 most popular referrers in the past %s days' % days,
        json.dumps([['Referrer', 'Count']] + list(stats_cursor)), 'table'))

    data_rows = []
    stats_cursor.execute('''
        SELECT category_id, COUNT(*) FROM requests_''' + lang_code +
        ''' WHERE snippet_id IS NOT NULL AND category_id IS NOT NULL AND
        category_id != "all" AND status_code = 200
        AND DATEDIFF(NOW(), ts) < %s GROUP BY category_id
        ORDER BY COUNT(*) DESC LIMIT 30''', (days,))
    for category_id, count in stats_cursor:
        ch_cursor.execute('''
            SELECT title FROM categories WHERE id = %s''', (category_id,))
        title = list(ch_cursor)[0][0] if ch_cursor.rowcount else "(gone)"
        data_rows.append((title, count))
    graphs.append((
        '30 most popular categories in the past %s days' % days,
        json.dumps([['Category', 'Count']] + data_rows), 'table'))

    # FIXME don't assume tools labs?
    stats_cursor.execute('''
        SELECT user_agent, COUNT(*) FROM requests_''' + lang_code + '''
        WHERE status_code = 200 AND DATEDIFF(NOW(), ts) < %s
        AND referrer NOT LIKE "%%tools.wmflabs.org/citationhunt%%"
        AND user_agent IS NOT NULL
        GROUP BY user_agent ORDER BY COUNT(*) DESC LIMIT 30''', (days,))
    graphs.append((
        '30 most popular user agents in the past %s days' % days,
        json.dumps([['User agent', 'Count']] + list(stats_cursor)), 'table'))

    return flask.render_template('stats.html', graphs = graphs)
