#!/usr/bin/env python3

import os
import sys
import gzip
_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)

import chdb
import config

def dump_snippets_as_json(output_path_gz):
    cfg = config.get_localized_config()
    db = chdb.init_db(cfg.lang_code)
    cursor = db.cursor()

    cursor.execute(
        '''SELECT JSON_OBJECT(
            'id', id, 'page_id', article_id, 'snippet', snippet,
            'section', section, 'oldest_template_date', oldest_template_date,
            'title', title)
        FROM snippets
        JOIN articles
        ON articles.page_id = snippets.article_id''')
    with gzip.open(output_path_gz, 'wb') as gz:
        for (json_obj,) in cursor:
            gz.write((json_obj + '\n').encode('utf-8'))

if __name__ == '__main__':
    dump_snippets_as_json(sys.argv[1])
