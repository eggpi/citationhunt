#!/usr/bin/env python

'''
Assign categories to the pages in the CitationHunt database.

Usage:
    assign_categories.py [--max-categories=<n>] [--mysql-config=<FILE>]

Options:
    --max-categories=<n>   Maximum number of categories to use [default: inf].
    --mysql-config=<FILE>  MySQL config file [default: ./ch.my.cnf].
'''

from __future__ import unicode_literals

import sys
sys.path.append('../')

import config
import chdb as chdb_
from utils import *

import docopt

import re
import collections

log = Logger()

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

def load_hidden_categories(wpcursor):
    cfg = config.get_localized_config()
    wpcursor.execute('''
        SELECT cl_from FROM categorylinks WHERE
        cl_to = %s''', (cfg.hidden_category,))
    hidden_page_ids = [row[0] for row in wpcursor]
    return category_ids_to_names(wpcursor, hidden_page_ids)

def load_categories_for_page(wpcursor, pageid):
    wpcursor.execute('''
        SELECT cl_to FROM categorylinks WHERE cl_from = %s''', (pageid,))
    return set(CategoryName.from_wp_categorylinks(row[0]) for row in wpcursor)

def load_projectindex(tlcursor):
    # WikiProject categories are added to the talk page, not the article.
    # We use a special table on Tools Labs to map talk pages to projects,
    # which will hopefully be more broadly available soon
    # (https://phabricator.wikimedia.org/T131578)
    projectindex_cache = {}
    tlcursor.execute('SELECT pi_project, pi_page from projectindex')
    for project, page in tlcursor:
        project = CategoryName.from_tl_projectindex(project)
        page = d(page)
        projectindex_cache.setdefault(page, set()).add(project)
    return projectindex_cache

def load_pinned_categories_for_page(wpcursor, projectindex, pageid):
    wpcursor.execute('SELECT page_title FROM page WHERE page_id = %s',
        (pageid,))
    rows = list(wpcursor)
    if not rows:
        return set()
    title = d(rows[0][0])
    talk_page_title = 'Talk:' + title
    return set(projectindex.get(talk_page_title, []))

def category_is_usable(catname, hidden_categories):
    assert isinstance(catname, CategoryName)
    if catname in hidden_categories:
        return False
    cfg = config.get_localized_config()
    for regexp in cfg.category_name_regexps_blacklist:
        if re.search(regexp, catname):
            return False
    return True

def choose_categories(categories_to_ids, unsourced_pageids, max_categories):
    categories = set()
    category_sets = categories_to_ids.items()
    total = float(len(unsourced_pageids))

    desired_pages_per_category = 20
    category_costs = {
        catname: abs(len(pageids) - desired_pages_per_category) + 1.0
        for catname, pageids in category_sets
    }

    def key_fn(cs):
        catname, pageids = cs
        return len(pageids & unsourced_pageids) / category_costs[catname]

    while unsourced_pageids and len(categories) < max_categories:
        category_sets.sort(key = key_fn)
        catname, covered_pageids = category_sets.pop()
        categories.add((catname, frozenset(covered_pageids)))
        unsourced_pageids -= covered_pageids

        rem = len(unsourced_pageids)
        log.progress('%d uncategorized pages (%d %%)' % \
            (rem, (rem / total) * 100))
    log.info('finished with %d categories' % len(categories))
    return categories

def build_snippets_links_for_category(cursor, category_id):
    cursor.execute('''
        SELECT snippets.id FROM snippets, articles_categories, articles
        WHERE snippets.article_id = articles_categories.article_id AND
        articles.page_id = articles_categories.article_id AND
        articles_categories.category_id = %s ORDER BY articles.title;''',
        (category_id,))
    snippets = [r[0] for r in cursor]

    prev = snippets[0]
    for s in snippets[1:] + [snippets[0]]:
        cursor.execute('''
            INSERT INTO snippets_links VALUES (%s, %s, %s)
        ''', (prev, s, category_id))
        prev = s

def update_citationhunt_db(chdb, categories):
    for n, (catname, pageids) in enumerate(categories):
        category_id = category_name_to_id(catname)
        def insert(cursor):
            cursor.execute('''
                INSERT IGNORE INTO categories VALUES(%s, %s)
            ''', (category_id, unicode(catname)))

            prev = ''
            for page_id in pageids:
                cursor.execute('''
                    INSERT INTO articles_categories VALUES (%s, %s)
                ''', (page_id, category_id))
            build_snippets_links_for_category(cursor, category_id)
        chdb.execute_with_retry(insert)

        log.progress('saved %d categories' % (n + 1))
    log.info('all done.')

def reset_chdb_tables(cursor):
    log.info('resetting articles_categories table...')
    cursor.execute('DELETE FROM articles_categories')
    log.info('resetting categories table...')
    cursor.execute('DELETE FROM categories')
    log.info('resetting snippets_links table...')
    cursor.execute('DELETE FROM snippets_links')

def assign_categories(max_categories, mysql_default_cnf):
    cfg = config.get_localized_config()
    chdb = chdb_.init_scratch_db()
    wpdb = chdb_.init_wp_replica_db()

    chdb.execute_with_retry(reset_chdb_tables)
    unsourced_pageids = load_unsourced_pageids(chdb)

    projectindex = {}
    if running_in_tools_labs() and cfg.lang_code == 'en':
        tldb = chdb_.init_projectindex_db()
        tlcursor = tldb.cursor()

        projectindex = load_projectindex(tlcursor)
        log.info('loaded projects for %d talk pages (%s...)' % \
            (len(projectindex), projectindex.values()[0]))

    hidden_categories = wpdb.execute_with_retry(load_hidden_categories)
    log.info('loaded %d hidden categories (%s...)' % \
        (len(hidden_categories), next(iter(hidden_categories))))

    categories_to_ids = collections.defaultdict(set)
    pinned_categories_to_ids = collections.defaultdict(set)
    page_ids_with_no_categories = 0
    for n, pageid in enumerate(list(unsourced_pageids)):
        categories = wpdb.execute_with_retry(load_categories_for_page, pageid)
        pinned_categories = (wpdb.execute_with_retry(
            load_pinned_categories_for_page, projectindex, pageid)
            if projectindex else set())
        # Filter both kinds of categories and build the category -> pageid
        # indexes
        page_has_at_least_one_category = False
        for catname in categories:
            if category_is_usable(catname, hidden_categories):
                page_has_at_least_one_category = True
                categories_to_ids[catname].add(pageid)
        for catname in pinned_categories:
            if category_is_usable(catname, hidden_categories):
                page_has_at_least_one_category = True
                pinned_categories_to_ids[catname].add(pageid)
        if not page_has_at_least_one_category:
            unsourced_pageids.remove(pageid)
            page_ids_with_no_categories += 1
        log.progress('loaded categories for %d pageids' % (n + 1))

    log.info('%d pages lack usable categories!' % page_ids_with_no_categories)
    log.info('found %d usable categories (%s, %s...)' % \
        (len(categories_to_ids), categories_to_ids.keys()[0],
        categories_to_ids.keys()[1]))
    if pinned_categories_to_ids:
        log.info('%d pinned categories (%s, %s)' % \
            (len(pinned_categories_to_ids), pinned_categories_to_ids.keys()[0],
             pinned_categories_to_ids.keys()[1]))

    categories = choose_categories(categories_to_ids, unsourced_pageids,
        max_categories)
    categories |= set(
        (k, frozenset(v)) for k, v in pinned_categories_to_ids.items())

    update_citationhunt_db(chdb, categories)
    wpdb.close()
    chdb.close()
    return 0

if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    max_categories = float(args['--max-categories'])
    mysql_default_cnf = args['--mysql-config']
    ret = assign_categories(max_categories, mysql_default_cnf)
    sys.exit(ret)
