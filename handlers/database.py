"""Functions that access the databases in the Flask app.
"""

import chdb
from .common import *
from utils import *

import itertools

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
            articles.title, snippets.oldest_template_date
            FROM snippets, articles WHERE snippets.id = %s
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

def query_snippet_by_intersection(lang_code, inter_id):
    cursor = get_db(lang_code).cursor()
    with log_time('select with category'):
        cursor.execute('''
            SELECT snippets.id FROM snippets, articles_intersections
            WHERE snippets.article_id = articles_intersections.article_id AND
            articles_intersections.inter_id = %s ORDER BY RAND()
            LIMIT 1;''', (inter_id,))
        return cursor.fetchone()

def query_random_snippet(lang_code):
    cursor = get_db(lang_code).cursor()
    cursor.execute(
        'SELECT id FROM snippets WHERE RAND() < 1e-4 LIMIT 1;')
    return cursor.fetchone()

def query_next_id_in_category(lang_code, curr_id, cat_id):
    cursor = get_db(lang_code).cursor()
    with log_time('select next id'):
        cursor.execute('''
            SELECT next FROM snippets_links WHERE prev = %s
            AND cat_id = %s''', (curr_id, cat_id))
        return cursor.fetchone()

def query_next_id_in_intersection(lang_code, curr_id, inter_id):
    cursor = get_db(lang_code).cursor()
    with log_time('select next id'):
        cursor.execute('''
            SELECT next FROM snippets_links WHERE prev = %s
            AND inter_id = %s''', (curr_id, inter_id))
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

def search_article_title(lang_code, needle, max_results):
    cursor = get_db(lang_code).cursor()
    needle = '%' + needle + '%'
    with log_time('search title & snippets'):
        cursor.execute('''
            SELECT articles.page_id, articles.title, GROUP_CONCAT(snippets.id)
            FROM articles, snippets
            WHERE articles.title LIKE %s
            AND snippets.article_id = articles.page_id
            GROUP BY articles.page_id, articles.title
            LIMIT %s''', (needle, max_results))
    return [{
        'page_id': row[0], 'title': row[1], 'snippets': row[2].split(',')
    } for row in cursor]

def query_fixed_snippets(lang_code, from_ts):
    with get_stats_db().cursor() as cursor:
        cursor.execute(
            'SELECT COUNT(*) FROM fixed_%s '
            'WHERE clicked_ts BETWEEN %%s AND NOW()' % lang_code,
            (from_ts,))
        nfixed = cursor.fetchone()
    return nfixed[0] if nfixed else 0

def query_fixed_revisions(lang_code, start_days):
    with get_stats_db().cursor() as cursor:
        cursor.execute(
            'SELECT rev_id FROM fixed_' + lang_code +
            ' WHERE DATEDIFF(NOW(), clicked_ts) < %s', (start_days,))
        return [row[0] for row in cursor.fetchall()]

def query_rev_users(lang_code, rev_ids):
    wpdb = chdb.init_wp_replica_db(lang_code)
    with wpdb.cursor() as cursor:
        cursor.execute(
            'SELECT actor_name FROM actor '
            'JOIN revision_userindex ON actor_id = rev_actor '
            'WHERE NOT ISNULL(actor_user) AND rev_id IN %s', (tuple(rev_ids),))
        return [row[0].decode('utf-8') for row in cursor.fetchall()]

def populate_snippets_links(cursor,
        intersection_ids = None, category_ids = None):
    assert bool(intersection_ids) ^ bool(category_ids), \
        'Can only pass one of intersection_ids and category_ids!'
    if intersection_ids:
        cursor.execute('''
            SELECT articles_intersections.inter_id, snippets.id
            FROM snippets, articles_intersections, articles
            WHERE snippets.article_id = articles_intersections.article_id AND
            articles.page_id = articles_intersections.article_id AND
            articles_intersections.inter_id IN %s
            ORDER BY articles_intersections.inter_id, articles.title;''',
            (tuple(intersection_ids),))
        insert_tuple = '(%s, %s, NULL, %s)'
    else:
        cursor.execute('''
            SELECT articles_categories.category_id, snippets.id
            FROM snippets, articles_categories, articles
            WHERE snippets.article_id = articles_categories.article_id AND
            articles.page_id = articles_categories.article_id AND
            articles_categories.category_id IN %s
            ORDER BY articles_categories.category_id, articles.title;''',
            (tuple(category_ids),))
        insert_tuple = '(%s, %s, %s, NULL)'
    cursor.executemany('INSERT INTO snippets_links VALUES ' + insert_tuple,
        ((p, n, id)
        for id, group in it.groupby(cursor, lambda id_sid: id_sid[0])
        for p, n in pair_with_next(snippet_id for (_, snippet_id) in group)))

def create_intersection(lang_code, page_ids, max_pages, expiration_days):
    db = get_db(lang_code)
    # First, intersect the page ids with the ones we already have. We assume
    # that there are no snippets to be obtained from the ones not in the
    # intersection (or they would be in our db), so we throw them away.
    intersection = db.execute_with_retry_s('''
        SELECT page_id, title
        FROM articles WHERE page_id IN %s
        ORDER BY title''', tuple(page_ids))
    if intersection is None:
        return '', []
    page_ids = [row[0] for row in intersection][:max_pages]
    titles = [row[1] for row in intersection][:max_pages]
    inter_id = mkid('|'.join(title.lower() for title in sorted(titles)))

    def insert_intersection(cursor):
        with chdb.ignore_warnings():
            # Add the intersection if needed then set its expiration in a
            # separate statement, because we want to bump the expiration of the
            # intersection if it already exists. We could use REPLACE instead of
            # INSERT IGNORE/UPDATE but that's a MySQL extension.
            cursor.execute('''
                INSERT IGNORE INTO intersections VALUES (%s, 0)
            ''', (inter_id,))
            cursor.execute('''
                UPDATE intersections
                SET expiration = DATE_ADD(NOW(), INTERVAL %s DAY)
                WHERE id = %s
            ''', (expiration_days, inter_id))
            cursor.executemany('''
                INSERT IGNORE INTO articles_intersections VALUES (%s, %s)
            ''', [(page_id, inter_id) for page_id in page_ids])
            populate_snippets_links(cursor, intersection_ids = [inter_id])
        return inter_id, page_ids
    return db.execute_with_retry(insert_intersection)

def get_snippets_in_articles(lang_code, page_ids, max_snippets):
    db = get_db(lang_code)
    rows = db.execute_with_retry_s('''
        SELECT articles.page_id, snippets.id
        FROM articles, snippets
        WHERE articles.page_id = snippets.article_id
        AND articles.page_id IN %s
        ORDER BY articles.title
        LIMIT %s''', tuple(page_ids), max_snippets)
    if rows is None:
        return {}
    return {title: [r[1] for r in rows]
            for title, rows in itertools.groupby(
                rows, key = lambda r: r[0])}
