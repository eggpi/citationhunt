import flask

import chdb
import config
from common import *

import os
import json
import re

def load_is_not_crawler_sql():
    crawler_user_agents = json.load(
        file(os.path.join(os.path.dirname(__file__),
            'crawler-user-agents', 'crawler-user-agents.json')))
    referrer_spam_blacklist = file(os.path.join(os.path.dirname(__file__),
            'referrer-spam-blacklist', 'spammers.txt'))
    return ' AND '.join([
        'user_agent NOT REGEXP "%s"' % obj['pattern']
        for obj in crawler_user_agents
    ] + [
        'referrer NOT REGEXP "%s"' % domain.decode('utf-8').strip()
        for domain in referrer_spam_blacklist
    ])

def log_request(response):
    lang_code = getattr(flask.request, 'lang_code', None)
    id = flask.request.args.get('id')
    cat = flask.request.args.get('cat')
    url = flask.request.url
    prefetch = (flask.request.headers.get('purpose') == 'prefetch' or
                flask.request.headers.get('X-Moz') == 'prefetch')
    user_agent = flask.request.headers.get('User-Agent', 'NULL')
    referrer = flask.request.referrer
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
    is_not_crawler_sql = load_is_not_crawler_sql()

    graphs = [] # title, data table as array, type
    stats_cursor = get_stats_db().cursor()
    ch_cursor = get_db(lang_code).cursor()

    stats_cursor.execute('''
        SELECT DATE_FORMAT(ts, GET_FORMAT(DATE, 'ISO')) AS dt, COUNT(*)
        FROM requests_''' + lang_code +
        ''' WHERE snippet_id IS NOT NULL AND status_code = 200
        AND DATEDIFF(NOW(), ts) < %s AND ''' + is_not_crawler_sql +
        ''' GROUP BY dt ORDER BY dt''', (days,))
    graphs.append((
        'Number of snippets served in the past %s days' % days,
        json.dumps([['Date', lang_code]] + list(stats_cursor)), 'line'))

    stats_cursor.execute('''
        SELECT DATE_FORMAT(ts, GET_FORMAT(DATE, 'ISO')) AS dt,
        COUNT(DISTINCT user_agent) FROM requests_''' + lang_code + '''
        WHERE snippet_id IS NOT NULL AND status_code = 200 AND
        user_agent != "NULL" AND DATEDIFF(NOW(), ts) < %s
        AND ''' + is_not_crawler_sql + ''' GROUP BY dt ORDER BY dt''',
        (days,))
    graphs.append((
        'Distinct user agents in the past %s days' % days,
        json.dumps([['Date', lang_code]] + list(stats_cursor)), 'line'))

    stats_cursor.execute('''
        SELECT DATE_FORMAT(ts, GET_FORMAT(DATE, 'ISO')) AS dt, COUNT(*)
        FROM requests_''' + lang_code +
        ''' WHERE url LIKE '%%redirect%%' AND status_code = 302
        AND DATEDIFF(NOW(), ts) < %s AND ''' + is_not_crawler_sql +
        ''' GROUP BY dt ORDER BY dt''', (days,))
    graphs.append((
        'Number of redirects to article in the past %s days' % days,
        json.dumps([['Date', lang_code]] + list(stats_cursor)), 'line'))

    # FIXME don't assume tools labs?
    stats_cursor.execute('''
        SELECT referrer, COUNT(*) FROM requests_''' + lang_code + '''
        WHERE status_code = 200 AND DATEDIFF(NOW(), ts) < %s
        AND referrer NOT LIKE "%%tools.wmflabs.org/citationhunt%%"
        AND ''' + is_not_crawler_sql +
        ''' GROUP BY referrer ORDER BY COUNT(*) DESC LIMIT 30
    ''', (days,))
    graphs.append((
        '30 most popular referrers in the past %s days' % days,
        json.dumps([['Referrer', 'Count']] + list(stats_cursor)), 'table'))

    data_rows = []
    stats_cursor.execute('''
        SELECT category_id, COUNT(*) FROM requests_''' + lang_code +
        ''' WHERE snippet_id IS NOT NULL AND category_id IS NOT NULL AND
        category_id != "all" AND status_code = 200
        AND DATEDIFF(NOW(), ts) < %s AND ''' + is_not_crawler_sql +
        ''' GROUP BY category_id ORDER BY COUNT(*) DESC LIMIT 30
    ''', (days,))
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
        AND ''' + is_not_crawler_sql +
        ''' GROUP BY user_agent ORDER BY COUNT(*) DESC LIMIT 30
    ''', (days,))
    graphs.append((
        '30 most popular user agents in the past %s days' % days,
        json.dumps([['User agent', 'Count']] + list(stats_cursor)), 'table'))

    return flask.render_template('stats.html', graphs = graphs)
