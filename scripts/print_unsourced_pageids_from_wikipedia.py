#!/usr/bin/env python

import sys
sys.path.append('../')

import chdb

db = chdb.init_wp_replica_db()
cursor = db.cursor()
cursor.execute('SELECT cl_from FROM categorylinks WHERE cl_to ='
    '"All_articles_with_unsourced_statements"')
for row in cursor:
    print row[0]

