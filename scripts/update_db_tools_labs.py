#!/usr/bin/env python

import os
import sys

script_dir = os.path.dirname(__file__)
sys.path.append(os.path.join(script_dir, '..'))

import config

import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Update the CitationHunt databases.')
    parser.add_argument('--lang-code', dest = 'lang_code',
        help='One of the language codes in ../config.py')
    args = parser.parse_args()

    if args.lang_code not in config.lang_code_to_config:
        print >>sys.stderr, 'Invalid lang code! Use one of: ',
        print >>sys.stderr, config.lang_code_to_config.keys()
        parser.print_usage()
        sys.exit(1)

    cfg = config.get_localized_config(args.lang_code)
    os.environ['CH_LANG'] = args.lang_code
    os.environ['CH_MAX_CATEGORIES'] = str(cfg.max_categories)
    sys.exit(os.system(os.path.join(script_dir, 'update_db_tools_labs.sh')))
