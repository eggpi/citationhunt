#!/usr/bin/env python

import sys
sys.path.append('../')

import chdb
import config

cfg = config.get_localized_config()
db = chdb.init_wp_replica_db()
cursor = db.cursor()

categories = set([cfg.citation_needed_category])
while True:
    cursor.execute(
        'SELECT cl_from, cl_type FROM categorylinks WHERE (' +
        ' OR '.join(['cl_to = %s'] * len(categories)) + ')', categories)
    subcategories = set()
    for page_id, type in cursor:
        if type == 'page':
            print page_id
        elif type == 'subcat':
            subcategories.add(page_id)
    if not subcategories:
        break

    # need to convert the page ids of subcategories into page
    # titles so we can query recursively
    cursor.execute(
        'SELECT page_title FROM page WHERE (' +
        ' OR '.join(['page_id = %s'] * len(subcategories)) + ')',
        subcategories)
    categories = set([r[0] for r in cursor])
