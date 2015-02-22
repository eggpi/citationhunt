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

import workerpool

import docopt
import networkx

import sys
import sqlite3
import itertools
import collections
import multiprocessing

UNSOURCED_STMTS_CAT_ID = '9329647' # not really needed
UNSOURCED_STMTS_CAT_NAME = 'All articles with unsourced statements'
UNSOURCED_STMTS_CAT_NAME_ = UNSOURCED_STMTS_CAT_NAME.replace(' ', '_')

class TupleParser(workerpool.Worker):
    def setup(self):
        pass

    def work(self, values):
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

    def done(self):
        pass

def parse_sql_catlinks(sqlfilename, receiver):
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

    worker = TupleParser()
    wp = workerpool.WorkerPool(worker, receiver)
    for valstr in gen_value_strings(sqlfilename):
        wp.post(valstr)
    wp.done()

class PrintUnsourcedReceiver(workerpool.Receiver):
    def setup(self):
        pass

    def receive(self, tups):
        for pageid, catname in tups:
            if catname == UNSOURCED_STMTS_CAT_NAME_:
                print pageid
                pass

    def done(self):
        pass

def print_unsourced_pageids(sqlfilename):
    parse_sql_catlinks(sqlfilename, PrintUnsourcedReceiver())

class GraphBuilderReceiver(workerpool.Receiver):
    def __init__(self, dbfilename):
        self.dbfilename = dbfilename

    def setup(self):
        self.catnames_to_ids = {}
        db = sqlite3.connect(self.dbfilename)
        for catid, catname in db.execute('''SELECT id, name FROM cat'''):
            # normalize cname to the format used in catlinks
            assert catname.startswith('Category:')
            catname = catname[len('Category:'):].replace(' ', '_')
            self.catnames_to_ids[catname] = catid

        self.g = networkx.DiGraph() # page -> category

    def receive(self, tups):
        for pageid, catname in tups:
            catid = self.catnames_to_ids.get(catname, None)
            if catid is None:
                # sadly, looks like catlinks contains empty categories
                # and categories that have no id in pages-articles. we could
                # actually use them by using catname as the identifier, but
                # let's ignore them for now.
                continue

            self.g.add_edge(pageid, catid)

    def done(self):
        networkx.write_gpickle(self.g, 'catgraph.nx.pkl')

def build_category_graph(sqlfilename, dbfilename):
    parse_sql_catlinks(sqlfilename, GraphBuilderReceiver(dbfilename))

if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    if args['print-unsourced-pageids']:
        print_unsourced_pageids(args['<catlinks.sql>'])
    elif args['build-category-graph']:
        build_category_graph(args['<catlinks.sql>'],
            args['<citationhunt.sqlite3>'])
