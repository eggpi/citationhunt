#!/usr/bin/env python

import os
import sys
_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)

import chdb
import config
import handlers.database as database

def update_intersections():
    db = chdb.init_scratch_db()
    cfg = config.get_localized_config()

    db.execute_with_retry_s('DELETE FROM intersections')
    db.execute_with_retry_s('''
        INSERT INTO intersections SELECT * FROM %s
        WHERE expiration > NOW()''' % chdb.get_table_name(
            db, 'citationhunt', 'intersections'))

    db.execute_with_retry_s('DELETE FROM articles_intersections')
    db.execute_with_retry_s('''
        INSERT INTO articles_intersections SELECT * FROM %s
        WHERE article_id IN (SELECT page_id FROM articles)
        AND inter_id IN (SELECT id FROM intersections)''' % chdb.get_table_name(
            db, 'citationhunt', 'articles_intersections'))

    def update_snippets_links(cursor):
        cursor.execute('SELECT id FROM intersections')
        intersection_ids = [row[0] for row in cursor]
        if intersection_ids:
            database.populate_snippets_links(cursor,
                intersection_ids = intersection_ids)
    db.execute_with_retry(update_snippets_links)
    # delete empty intersections. should this surface an error to the user
    # instead?
    db.execute_with_retry_s(
        '''DELETE FROM intersections WHERE id NOT IN (
            SELECT inter_id FROM articles_intersections)''')

if __name__ == '__main__':
    update_intersections()
