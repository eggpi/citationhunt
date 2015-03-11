#!/usr/bin/env python

'''
Assign categories to the pages in the CitationHunt database.

Usage:
    assign_categories.py [--max-categories=<n>]

Options:
    --max-categories=<n>  Maximum number of categories to use [default: inf].
'''

from __future__ import unicode_literals

import sys
sys.path.append('../')

import chdb as chdb_
from utils import *

import docopt

import re
import pymysql
import collections

class CategoryName(unicode):
    '''
    The canonical format for categories, which is the one we'll use
    in the CitationHunt database: no Category: prefix and spaces instead
    of underscores.
    '''
    def __init__(self, ustr):
        assert isinstance(ustr, unicode)
        assert not ustr.startswith('Category:'), ustr
        assert '_' not in ustr, ustr
        unicode.__init__(self, ustr)

    @staticmethod
    def from_wp_categories(ustr):
        ustr = d(ustr)
        assert ustr.startswith('Category:')
        return CategoryName(ustr[len('Category:'):])

    def to_wp_categories(self):
        return 'Category:' + self

    @staticmethod
    def from_wp_categorylinks(ustr):
        ustr = d(ustr)
        assert not ustr.startswith('Category:')
        return CategoryName(ustr.replace('_', ' '))

def category_ids_to_names(wpcursor, category_ids):
    category_names = set()
    for pageid in category_ids:
        wpcursor.execute('''SELECT title FROM categories WHERE page_id = %s''',
            (pageid,))
        category_names.update(
            CategoryName.from_wp_categories(row[0])
            for row in wpcursor)
    return category_names

def category_name_to_id(catname):
    return mkid(catname)

def load_unsourced_pageids(chdb):
    return set(r[0] for r in chdb.execute('''SELECT page_id FROM articles'''))

def load_hidden_categories(wpcursor):
    wpcursor.execute('''
        SELECT cl_from FROM categorylinks WHERE
        cl_to = "Hidden_categories"''')
    hidden_page_ids = [row[0] for row in wpcursor]
    return category_ids_to_names(wpcursor, hidden_page_ids)

def load_categories_for_page(wpcursor, pageid):
    wpcursor.execute('''
        SELECT cl_to FROM categorylinks WHERE cl_from = %s''', (pageid,))
    return set(CategoryName.from_wp_categorylinks(row[0]) for row in wpcursor)

NUMBER_PATTERN = re.compile('.*[0-9]+.*')
def category_is_usable(catname, hidden_categories):
    assert isinstance(catname, CategoryName)
    return catname not in hidden_categories \
        and not re.match(NUMBER_PATTERN, catname) \
        and not catname.startswith('Pages ') \
        and not catname.startswith('Articles ')

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
        print >>sys.stderr, \
            '\r%d uncategorized pages (%d %%)' % (rem, (rem / total) * 100),
    print >>sys.stderr
    print >>sys.stderr, 'finished with %d categories' % len(categories)
    return categories

def update_citationhunt_db(chdb, wpcursor, categories):
    for n, (catname, pageids) in enumerate(categories):
        category_page_id = category_name_to_id(catname)
        with chdb:
            chdb.execute('''
                INSERT OR IGNORE INTO categories VALUES(?, ?)
            ''', (category_page_id, catname))

            for page_id in pageids:
                chdb.execute('''
                    UPDATE articles SET category_id = ? WHERE page_id = ?
                ''', (category_page_id, page_id))

        print >>sys.stderr, '\rsaved %d categories' % (n + 1),
    print >>sys.stderr

    # print >>sys.stderr, 'deleting unassigned pages and snippets'
    # with chdb:
    #    chdb.execute('''
    #       DELETE FROM categories WHERE id = "unassigned"
    #   ''')

def assign_categories(max_categories):
    wpdb = pymysql.Connect(
        user = 'root', database = 'wikipedia', charset = 'utf8')
    wpcursor = wpdb.cursor()

    chdb = chdb_.init_db()
    # chdb.execute('PRAGMA foreign_keys = ON')
    print >>sys.stderr, 'resetting articles table...'
    chdb.execute('UPDATE articles SET category_id = "unassigned"')
    print >>sys.stderr, 'resetting categories table...'
    chdb.execute('DELETE FROM categories WHERE id != "unassigned"')

    unsourced_pageids = load_unsourced_pageids(chdb)
    hidden_categories = load_hidden_categories(wpcursor)

    categories_to_ids = collections.defaultdict(set)
    page_ids_with_no_categories = 0
    for n, pageid in enumerate(list(unsourced_pageids)):
        page_has_at_least_one_category = False
        for catname in load_categories_for_page(wpcursor, pageid):
            if category_is_usable(catname, hidden_categories):
                page_has_at_least_one_category = True
                categories_to_ids[catname].add(pageid)
        if not page_has_at_least_one_category:
            unsourced_pageids.remove(pageid)
            page_ids_with_no_categories += 1
        print >>sys.stderr, '\rloaded categories for %d pageids' % (n + 1),
    print >>sys.stderr

    print >>sys.stderr, \
        '%d pages lack usable categories!' % page_ids_with_no_categories

    print >>sys.stderr, 'found %d usable categories (%s, %s...)' % \
        (len(categories_to_ids), categories_to_ids.keys()[0],
        categories_to_ids.keys()[1])

    categories = choose_categories(categories_to_ids, unsourced_pageids,
        max_categories)

    update_citationhunt_db(chdb, wpcursor, categories)

    wpdb.close()
    chdb.close()

if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    max_categories = float(args['--max-categories'])
    assign_categories(max_categories)
