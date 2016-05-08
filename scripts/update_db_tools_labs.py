#!/usr/bin/env python

import os
import sys
_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)

import utils
import config

import time
import commands
import argparse
import tempfile

def email(message, attachment):
    commands.getoutput(
        '/usr/bin/mail -s "%s" -a %s citationhunt.update@tools.wmflabs.org' % (
        message, attachment))
    time.sleep(2*60)

def ensure_db_config(cfg):
    xxwiki = cfg.lang_code + 'wiki'
    replica_my_cnf = os.path.expanduser('~/replica.my.cnf')

    ch_my_cnf = 'ch.my.cnf'
    with open(ch_my_cnf, 'w') as f:
        print >> f, file(replica_my_cnf).read(),
        print >> f, 'host=tools-db',

    wp_my_cnf = 'wp.my.cnf'
    with open(wp_my_cnf, 'w') as f:
        print >> f, file(replica_my_cnf).read(),
        print >> f, 'host=%s.labsdb' % xxwiki,

    return ch_my_cnf, wp_my_cnf

def update_db_tools_labs(cfg):
    # Should match the job's name in crontab
    logfile = 'citationhunt_update_' + cfg.lang_code + '.err'
    file(logfile, 'w').close()  # truncate logfile

    # FIXME Import and calll these scripts instead of shelling out?
    def run_script(script, cmdline = ''):
        scripts_dir = os.path.dirname(os.path.realpath(__file__))
        script_path = os.path.join(scripts_dir, script)
        cmdline = ' '.join([sys.executable, script_path, cmdline])
        print >>sys.stderr, 'Running %s' % cmdline
        status, output = commands.getstatusoutput(cmdline)
        print >>sys.stderr, output
        if status != 0:
            email('Failed at %s!' % script, logfile)
            sys.exit(1)

    os.environ['CH_LANG'] = cfg.lang_code
    ch_my_cnf, wp_my_cnf = ensure_db_config(cfg)
    unsourced = tempfile.NamedTemporaryFile()
    run_script(
        'print_unsourced_pageids_from_wikipedia.py', wp_my_cnf + ' > ' +
        unsourced.name)
    run_script('parse_live.py', unsourced.name)
    run_script(
        'assign_categories.py', '--max_categories=%d' % cfg.max_categories)
    run_script('install_new_database.py')
    email('All done!', logfile)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Update the CitationHunt databases.')
    parser.add_argument('lang_code',
        help='One of the language codes in ../config.py')
    args = parser.parse_args()

    if not (utils.running_in_tools_labs() and utils.running_in_virtualenv()):
        print >>sys.stderr, 'Not running in a virtualenv in Tools Labs!'
        sys.exit(1)

    if args.lang_code not in config.lang_code_to_config:
        print >>sys.stderr, 'Invalid lang code! Use one of: ',
        print >>sys.stderr, config.lang_code_to_config.keys()
        parser.print_usage()
        sys.exit(1)

    cfg = config.get_localized_config(args.lang_code)
    update_db_tools_labs(cfg)
