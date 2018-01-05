"""Functions that access the databases in the Flask app.

These are here for ease of mocking during testing only.
"""

# TODO: CREATE TEMPORARY TABLE and test based on those instead?

import chdb
from common import *
from utils import *

def query_category_by_id(lang_code, cat_id):
    cursor = get_db(lang_code).cursor()
    with log_time('get category by id'):
        cursor.execute('''
            SELECT id, title FROM categories WHERE id = %s
        ''', (cat_id,))
        return cursor.fetchone()

def query_snippet_by_id(lang_code, id):
    cursor = get_db(lang_code).cursor()
    with log_time('select snippet by id'):
        cursor.execute('''
            SELECT snippets.snippet, snippets.section, articles.url,
            articles.title FROM snippets, articles WHERE snippets.id = %s
            AND snippets.article_id = articles.page_id;''', (id,))
        return cursor.fetchone()

def query_snippet_by_category(lang_code, cat_id):
    cursor = get_db(lang_code).cursor()
    with log_time('select with category'):
        cursor.execute('''
            SELECT snippets.id FROM snippets, articles_categories
            WHERE snippets.article_id = articles_categories.article_id AND
            articles_categories.category_id = %s ORDER BY RAND()
            LIMIT 1;''', (cat_id,))
        return cursor.fetchone()

def query_random_snippet(lang_code):
    cursor = get_db(lang_code).cursor()
    cursor.execute(
        'SELECT id FROM snippets WHERE RAND() < 1e-4 LIMIT 1;')
    return cursor.fetchone()

def query_next_id(lang_code, curr_id, cat_id):
    cursor = get_db(lang_code).cursor()

    with log_time('select next id'):
        cursor.execute('''
            SELECT next FROM snippets_links WHERE prev = %s
            AND cat_id = %s''', (curr_id, cat_id))
        return cursor.fetchone()

def search_category(lang_code, needle, max_results):
    cursor = get_db(lang_code).cursor()
    needle = '%' + needle + '%'
    with log_time('search category & page count'):
        cursor.execute('''
            SELECT category_id, title, article_count
            FROM categories, category_article_count
            WHERE title LIKE %s
            AND category_article_count.category_id = categories.id
            LIMIT %s''', (needle, max_results))
    return [{
        'id': row[0], 'title': row[1], 'npages': row[2]
    } for row in cursor]

def query_fixed_snippets(lang_code, from_ts):
    with get_stats_db() as cursor:
        cursor.execute(
            'SELECT COUNT(*) FROM fixed_%s '
            'WHERE clicked_ts BETWEEN %%s AND NOW()' % lang_code,
            (from_ts,))
    nfixed = cursor.fetchone()
    return nfixed[0] if nfixed else 0

def query_fixed_revisions(lang_code, start_days):
    with get_stats_db() as cursor:
        cursor.execute(
            'SELECT rev_id FROM fixed_' + lang_code +
            ' WHERE DATEDIFF(NOW(), clicked_ts) < %s', (start_days,))
    return [row[0] for row in cursor.fetchall()]

def query_rev_users(lang_code, rev_ids):
    wpdb = chdb.init_wp_replica_db(lang_code)
    with wpdb as cursor:
        cursor.execute(
            'SELECT rev_user_text FROM revision_userindex '
            'WHERE rev_user != 0 AND rev_id IN %s', (tuple(rev_ids),))
    return [row[0] for row in cursor.fetchall()]
