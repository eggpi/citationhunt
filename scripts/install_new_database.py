#!/usr/bin/env python3

import os
import sys
_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)

import chdb

def sanity_check():
    sdb = chdb.init_scratch_db()
    snippet_count = sdb.execute_with_retry_s(
        '''SELECT COUNT(*) FROM snippets''')[0][0]
    assert snippet_count > 100

    article_count = sdb.execute_with_retry_s(
        '''SELECT COUNT(*) FROM articles''')[0][0]
    assert article_count > 100

if __name__ == '__main__':
    sanity_check()
    chdb.install_scratch_db()
