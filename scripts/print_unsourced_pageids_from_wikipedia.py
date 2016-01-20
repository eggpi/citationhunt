#!/usr/bin/env python

import sys
sys.path.append('../')

import chdb
import config

cfg = config.get_localized_config()
db = chdb.init_wp_replica_db()
cursor = db.cursor()
cursor.execute('SELECT cl_from FROM categorylinks WHERE cl_to = %s',
    (cfg.citation_needed_category,))
for row in cursor:
    print row[0]
