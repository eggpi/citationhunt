#!/usr/bin/env python3

import os
import sys
_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)

import chdb
import config
import utils

import time
import subprocess
import argparse
import tempfile
import dateutil.parser
import datetime
import traceback
import logging

def email(message):
    subprocess.getoutput(
        '/usr/bin/mail -s "%s" ' % message +
        ' citationhunt.update@tools.wmflabs.org')
    time.sleep(2*60)

def shell(logger, cmdline):
    logger.info('Running %s' % cmdline)
    status, output = subprocess.getstatusoutput(cmdline)
    for l in output.splitlines():
        logger.info(l)
    return status == 0

def expire_stats(cfg):
    stats_db = chdb.init_stats_db()
    with chdb.init_stats_db().cursor() as cursor, chdb.ignore_warnings():
        cursor.execute('DELETE FROM requests WHERE DATEDIFF(NOW(), ts) > %s',
                (cfg.stats_max_age_days,))

def _update_db_tools_labs(logger, cfg):
    os.environ['CH_LANG'] = cfg.lang_code
    chdb.initialize_all_databases()

    expire_stats(cfg)

    # FIXME Import and calll these scripts instead of shelling out?
    def run_script(script, cmdline = '', optional = False):
        scripts_dir = os.path.dirname(os.path.realpath(__file__))
        script_path = os.path.join(scripts_dir, script)
        cmdline = ' '.join([sys.executable, script_path, cmdline])
        assert shell(logger, cmdline) == True or optional

    unsourced = tempfile.NamedTemporaryFile()
    run_script(
        'print_unsourced_pageids_from_wikipedia.py', '> ' + unsourced.name)
    run_script('parse_live.py', unsourced.name)
    run_script('assign_categories.py')
    run_script('update_intersections.py')
    run_script('install_new_database.py')

    unsourced.close()  # deletes the file

def update_db_tools_labs(logger, cfg):
    try:
        _update_db_tools_labs(logger, cfg)
    except Exception as e:
        traceback.print_exc(file = sys.stderr)
        email('Failed to build database for %s' % cfg.lang_code)
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Update the CitationHunt databases.')
    parser.add_argument('lang_code',
        nargs='*',
        help='One of the language codes in ../config.py')
    args = parser.parse_args()

    for lang_code in args.lang_code:
        logname = 'citationhunt_update_' + lang_code
        logger = logging.getLogger(logname)
        utils.setup_logger_to_logfile(logger, logname + '.log')

        if lang_code not in config.LANG_CODES_TO_LANG_NAMES:
            logger.error('Invalid lang code {}!'.format(lang_code))
            continue

        if not utils.running_in_tools_labs():
            logger.error('Not running in Tools Labs!')
            sys.exit(1)

        cfg = config.get_localized_config(lang_code)
        update_db_tools_labs(logger, cfg)
