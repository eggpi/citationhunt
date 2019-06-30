#!/usr/bin/env python3

import os
import sys
_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)

import chdb
import config

def print_unsourced_ids_from_wikipedia():
    cfg = config.get_localized_config()
    db = chdb.init_wp_replica_db(cfg.lang_code)
    cursor = db.cursor()
    categories = set([cfg.citation_needed_category])
    while True:
        cursor.execute(
            'SELECT cl_from, cl_type FROM categorylinks WHERE (' +
            ' OR '.join(['cl_to = %s'] * len(categories)) + ')', categories)
        subcategories = set()
        for page_id, type in cursor:
            if type == b'page':
                print(page_id)
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

if __name__ == '__main__':
    print_unsourced_ids_from_wikipedia()
