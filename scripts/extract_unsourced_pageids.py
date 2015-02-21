#!/usr/bin/env python

import sys
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

        if catname == UNSOURCED_STMTS_CAT_NAME_:
            ret.append(pageid)
        tupstart = tupend + len('),(') - 1
    return ret

def parse_sql_catlinks(filename):
    def gen_value_strings(filename):
        INSERT_STMT_BEGIN = 'INSERT INTO `categorylinks` VALUES'
        with open(filename) as catlinks:
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
    values_gen = gen_value_strings(filename)

    all_results = collections.deque()
    while True:
        ichunk = itertools.islice(values_gen, 200 * nprocs)
        results = workers.map(sql_val_parser, ichunk)
        if not results:
            break

        for result in results:
            for pageid in result:
                print pageid

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print >>sys.stderr, 'usage: %s <categorylinks.sql>' % sys.argv[0]
        sys.exit(1)
    parse_sql_catlinks(sys.argv[1])
