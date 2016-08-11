#!/usr/bin/env python

'''
Assign categories to the pages in the CitationHunt database.

Usage:
    assign_categories.py [--mysql_config=<FILE>]

Options:
    --mysql_config=<FILE>  MySQL config file [default: ./ch.my.cnf].
'''

from __future__ import unicode_literals

import os
import sys
_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)

import config
import chdb as chdb_
from utils import *

import docopt

import cProfile
import itertools as it
import re
import collections
import pstats
import time

log = Logger()

def ichunk(iterable, chunk_size):
    it0 = iter(iterable)
    while True:
        it1, it2 = it.tee(it.islice(it0, chunk_size))
        next(it2)  # raises StopIteration if it0 is exhausted
        yield it1

class CategoryName(unicode):
    '''
    The canonical format for categories, which is the one we'll use
    in the CitationHunt database: no Category: prefix and spaces instead
    of underscores.
    '''
    def __new__(klass, ustr):
        assert isinstance(ustr, unicode)
        assert not ustr.startswith('Category:'), ustr
        assert '_' not in ustr, ustr
        return super(CategoryName, klass).__new__(klass, ustr)

    @staticmethod
    def from_wp_page(ustr):
        ustr = d(ustr)
        if ustr.startswith('Category:'):
            ustr = ustr[len('Category:'):]
        assert ' ' not in ustr, ustr
        return CategoryName(ustr.replace('_', ' '))

    @staticmethod
    def from_wp_categorylinks(ustr):
        ustr = d(ustr)
        if ustr.startswith('Category:'):
            ustr = ustr[len('Category:'):]
        return CategoryName(ustr.replace('_', ' '))

    @staticmethod
    def from_tl_projectindex(ustr):
        ustr = d(ustr)
        if ustr.startswith('Wikipedia:'):
            ustr = ustr[len('Wikipedia:'):]
        return CategoryName(ustr.replace('_', ' '))

def category_ids_to_names(wpcursor, category_ids):
    category_names = set()
    for pageid in category_ids:
        wpcursor.execute('''SELECT page_title FROM page WHERE page_id = %s''',
            (pageid,))
        category_names.update(
            CategoryName.from_wp_page(row[0])
            for row in wpcursor)
    return category_names

def category_name_to_id(catname):
    return mkid(catname)

def load_unsourced_pageids(chdb):
    cursor = chdb.cursor()
    cursor.execute('''SELECT page_id FROM articles''')
    return set(r[0] for r in cursor)

def load_hidden_categories(wpcursor, cfg):
    wpcursor.execute('''
        SELECT cl_from FROM categorylinks WHERE
        cl_to = %s''', (cfg.hidden_category,))
    hidden_page_ids = [row[0] for row in wpcursor]
    return category_ids_to_names(wpcursor, hidden_page_ids)

def load_categories_for_pages(wpcursor, pageids):
    wpcursor.execute('''
        SELECT cl_to, cl_from FROM categorylinks WHERE cl_from IN %s''',
        (tuple(pageids),))
    return ((CategoryName.from_wp_categorylinks(row[0]), row[1])
            for row in wpcursor)

def count_snippets_for_pages(chcursor):
    chcursor.execute(
        '''SELECT article_id, count(snippets.id) '''
        '''FROM snippets GROUP BY article_id''')
    return {row[0]: row[1] for row in chcursor}

def load_projectindex(tlcursor):
    # We use a special table on Tools Labs to map page IDs to projects,
    # which will hopefully be more broadly available soon
    # (https://phabricator.wikimedia.org/T131578)
    query = """
    SELECT project_title, page_id
    FROM enwiki_index
    JOIN enwiki_page ON index_page = page_id
    JOIN enwiki_project ON index_project = project_id
    WHERE page_ns = 0 AND page_is_redirect = 0
    """
    tlcursor.execute(query)
    return ((CategoryName.from_tl_projectindex(row[0]), row[1])
            for row in tlcursor)

def category_is_usable(cfg, catname, hidden_categories):
    assert isinstance(catname, CategoryName)
    if catname in hidden_categories:
        return False
    for regexp in cfg.category_name_regexps_blacklist:
        if re.search(regexp, catname):
            return False
    return True

def build_snippets_links_for_category(cursor, category_ids):
    def pair_with_next(iterator):
        """
        Given an iterator (..., x, y, z, w, ...), returns another iterator of
        tuples that pair each element to its successor, that is
        (..., (x, y), (y, z), (z, w), ...).

        The iterator "wraps around" at the end, that is, the last element is
        paired with the first.
        """

        i1, i2 = it.tee(iterator)
        return it.izip(i1, it.chain(i2, [next(i2)]))

    # Populate the snippets_links table with pairs of snippets in the same
    # category, so each article "points" to the next one in that category.
    # The snippets are sorted by the title of their corresponding article.

    # First, query all categories and snippets, in the proper order
    cursor.execute('''
        SELECT articles_categories.category_id, snippets.id
        FROM snippets, articles_categories, articles
        WHERE snippets.article_id = articles_categories.article_id AND
        articles.page_id = articles_categories.article_id AND
        articles_categories.category_id IN %s
        ORDER BY articles_categories.category_id, articles.title;''',
        (tuple(category_ids),))

    # Now we indulge in some itertools magic to produce the pairs (or rather,
    # triplets, as they also include the category id) that we want to insert.
    # We want to use executemany for performance; the use of iterators saves
    # some memory, but really I just wanted to look cool.
    cursor.executemany('''
        INSERT INTO snippets_links VALUES (%s, %s, %s)
    ''', ((p, n, category_id)
        for category_id, group in it.groupby(cursor, lambda (cid, sid): cid)
        for p, n in pair_with_next(snippet_id for (_, snippet_id) in group)))

def update_citationhunt_db(chdb, category_name_id_and_page_ids):
    def insert(cursor, chunk):
        cursor.executemany('''
            INSERT IGNORE INTO categories VALUES (%s, %s)
        ''', ((category_id, category_name)
            for category_name, category_id, _ in chunk))
        cursor.executemany('''
            INSERT INTO articles_categories VALUES (%s, %s)
        ''', ((pageid, catid)
            for _, catid, pageids in chunk for pageid in pageids))
        build_snippets_links_for_category(cursor,
            (cid for (_, cid, _) in chunk))

    for c in ichunk(category_name_id_and_page_ids, 4096):
        chdb.execute_with_retry(insert, list(c))

def reset_chdb_tables(cursor):
    log.info('resetting articles_categories table...')
    cursor.execute('DELETE FROM articles_categories')
    log.info('resetting categories table...')
    cursor.execute('DELETE FROM categories')
    log.info('resetting snippets_links table...')
    cursor.execute('DELETE FROM snippets_links')

def assign_categories(mysql_default_cnf):
    cfg = config.get_localized_config()
    profiler = cProfile.Profile()
    if cfg.profile:
        profiler.enable()
    start = time.time()

    chdb = chdb_.init_scratch_db()
    wpdb = chdb_.init_wp_replica_db()

    chdb.execute_with_retry(reset_chdb_tables)
    unsourced_pageids = load_unsourced_pageids(chdb)

    # Load a list of (wikiproject, page ids)
    projectindex = []
    if running_in_tools_labs() and cfg.lang_code == 'en':
        tldb = chdb_.init_projectindex_db()
        tlcursor = tldb.cursor()
        projectindex = load_projectindex(tlcursor)
        log.info('loaded %d entries from projectinfo (%s...)' % \
            (len(projectindex), projectindex[0][0]))

    # Load a set() of hidden categories
    hidden_categories = wpdb.execute_with_retry(
        load_hidden_categories, cfg)
    log.info('loaded %d hidden categories (%s...)' % \
        (len(hidden_categories), next(iter(hidden_categories))))

    # Load all usable categories into a dict category -> [page ids]
    category_to_page_ids = {}
    for c, p in projectindex:
        category_to_page_ids.setdefault(c, []).append(p)
    for c in ichunk(unsourced_pageids, 10000):
        for c, p in wpdb.execute_with_retry(load_categories_for_pages, c):
            if category_is_usable(cfg, c, hidden_categories):
                category_to_page_ids.setdefault(c, []).append(p)

    # Now find out how many snippets each category has
    category_to_snippet_count = {}
    page_id_to_snippet_count = chdb.execute_with_retry(count_snippets_for_pages)
    for category, page_ids in category_to_page_ids.iteritems():
        category_to_snippet_count[category] = sum(
            page_id_to_snippet_count.get(p, 0) for p in page_ids)

    # And keep only the ones with at least two.
    category_name_id_and_page_ids = [
        (unicode(category), category_name_to_id(category), page_ids)
        for category, page_ids in category_to_page_ids.iteritems()
        if category_to_snippet_count[category] >= 2
    ]
    log.info('finished with %d categories' % len(category_name_id_and_page_ids))

    update_citationhunt_db(chdb, category_name_id_and_page_ids)
    wpdb.close()
    chdb.close()
    log.info('all done in %d seconds.' % (time.time() - start))

    if cfg.profile:
        profiler.disable()
        pstats.Stats(profiler).sort_stats('cumulative').print_stats(
            30, 'assign_categories.py')
    return 0

if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    mysql_default_cnf = args['--mysql_config']
    ret = assign_categories(mysql_default_cnf)
    sys.exit(ret)
