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
    templates = [t.replace(' ', '_') for t in cfg.citation_needed_templates]

    db = chdb.init_wp_replica_db(cfg.lang_code)
    cursor = db.cursor()

    or_clause = (
        '(' + 'OR '.join(['lt_title = %s'] * len(templates)) + ')'
    )
    # https://www.mediawiki.org/wiki/Help:Namespaces
    cursor.execute(
        'SELECT DISTINCT tl_from FROM templatelinks '
        'JOIN linktarget ON templatelinks.tl_target_id = linktarget.lt_id '
        'LEFT JOIN page_restrictions ON pr_page = tl_from '
        'WHERE tl_from_namespace = 0 AND lt_namespace = 10 AND '
        '(pr_type IS NULL OR pr_type != "edit") AND ' + or_clause, templates)
    for (page_id,) in cursor:
        print(page_id)

if __name__ == '__main__':
    print_unsourced_ids_from_wikipedia()
