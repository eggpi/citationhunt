#!/usr/bin/env python

'''
The catlinks parser for CitationHunt.

Usage:
    parse_catlinks.py print-unsourced-pageids <catlinks.sql>
    parse_catlinks.py build-category-graph <catlinks.sql> <citationhunt.sqlite3>

With print-unsourced-pageids, the pageids of all pages belonging to
Category:All_articles_with_unsourced_statements will be printed to stdout, one
per line.

With build-category-graph, a catgraph.nx.pkl file will be generated, containing a
pickle'd networkx DiGraph of categories. Each node contains a pageid and has
edges to its parent category.
'''

import docopt
import networkx

import sys
import pickle
import sqlite3
import itertools
import collections
import multiprocessing

UNSOURCED_STMTS_CAT_ID = '9329647' # not really needed
UNSOURCED_STMTS_CAT_NAME = 'All articles with unsourced statements'
UNSOURCED_STMTS_CAT_NAME_ = UNSOURCED_STMTS_CAT_NAME.replace(' ', '_')

def sql_val_parser(values):
    ret = collections.deque()
    tupstart = 0
    finished = False
    while not finished:
        assert values[tupstart] == '('

        tupend = values.find('),(', tupstart + 1)
        if tupend == -1:
            tupend = values.find(');', tupstart + 1)
            assert tupend == len(values) - len(');')
            finished = True

        pageid, rest = values[tupstart+1:tupend].split(',', 1)
        catname = rest[:rest.find("','")+1]
        assert catname[0] == catname[-1] == "'"
        catname = catname[1:-1]
        ret.append((pageid, catname))
        tupstart = tupend + len('),(') - 1
    return ret

def parse_sql_catlinks(sqlfilename, callback):
    def gen_value_strings(filename):
        INSERT_STMT_BEGIN = 'INSERT INTO `categorylinks` VALUES'
        with open(sqlfilename) as catlinks:
            # skip header
            for line in catlinks:
                if line.startswith(INSERT_STMT_BEGIN):
                    break

            for line in itertools.chain([line], catlinks):
                if not line.startswith(INSERT_STMT_BEGIN):
                    return
                values = line[len(INSERT_STMT_BEGIN):].strip()
                yield values

    nprocs = multiprocessing.cpu_count()
    workers = multiprocessing.Pool(nprocs)
    values_gen = gen_value_strings(sqlfilename)

    all_results = collections.deque()
    while True:
        ichunk = itertools.islice(values_gen, 200 * nprocs)
        results = workers.map(sql_val_parser, ichunk)
        if not results:
            break

        for result in results:
            for pageid, catname in result:
                callback(pageid, catname)

def print_unsourced_pageids(sqlfilename):
    def row_callback(pageid, catname):
        if catname == UNSOURCED_STMTS_CAT_NAME_:
            print pageid
    parse_sql_catlinks(sqlfilename, row_callback)

def build_category_graph(sqlfilename, dbfilename):
    db = sqlite3.connect(dbfilename)
    catnames_to_ids = {}
    for catid, catname in db.execute('''SELECT id, name FROM cat'''):
        # normalize cname to the format used in catlinks
        assert catname.startswith('Category:')
        catname = catname[len('Category:'):].replace(' ', '_')
        catnames_to_ids[catname] = catid

    g = networkx.DiGraph() # page -> its category
    def row_callback(pageid, catname):
        catid = catnames_to_ids.get(catname, None)
        if catid is None:
            # sadly, looks like catlinks contains empty categories and
            # categories that have no id in pages-articles. we could actually
            # use them by using catname as its identifier, but let's ignore them
            # for now.
            return
        g.add_edge(pageid, catid)

    parse_sql_catlinks(sqlfilename, row_callback)
    with open('catgraph.nx.pkl', 'wb') as gf:
        pickle.dump(g, gf)

if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    if args['print-unsourced-pageids']:
        parse_sql_catlinks(args['<catlinks.sql>'], print_category_pageid)
    elif args['build-category-graph']:
        build_category_graph(args['<catlinks.sql>'],
            args['<citationhunt.sqlite3>'])
