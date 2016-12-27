#!/usr/bin/env python

import errno
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
import commands
import argparse
import tempfile
import dateutil.parser
import datetime
import traceback

def email(message, attachment):
    commands.getoutput(
        '/usr/bin/mail -s "%s" -a %s citationhunt.update@tools.wmflabs.org' % (
        message, attachment))
    time.sleep(2*60)

def shell(cmdline):
    print >>sys.stderr, 'Running %s' % cmdline
    status, output = commands.getstatusoutput(cmdline)
    print >>sys.stderr, output
    return status == 0

# Thanks, StackOverflow! https://stackoverflow.com/questions/600268
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

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

def get_db_names_to_archive(lang_code):
    database_names = []
    for db in [chdb.init_db(lang_code), chdb.init_stats_db()]:
        with db as cursor:
            cursor.execute('SELECT DATABASE()')
            database_names.append(cursor.fetchone()[0])
    return database_names

def delete_old_archives(archive_dir, archive_duration_days):
    try:
        all_archives = os.listdir(archive_dir)
    except OSError:
        print >>sys.stderr, 'No archives to delete!'
        return

    for a in all_archives:
        # format: YYYYMMDD-HHMM.sql.gz
        when = dateutil.parser.parse(a.split('.', 1)[0])
        age = (datetime.datetime.today() - when).days
        if age > archive_duration_days:
            print >>sys.stderr, 'Archive %s is %d days old, deleting' % (a, age)
            os.remove(os.path.join(archive_dir, a))

def archive_database(ch_my_cnf, cfg):
    dbs_to_archive = get_db_names_to_archive(cfg.lang_code)
    archive_dir = os.path.join(cfg.archive_dir, cfg.lang_code)
    if cfg.archive_duration_days > 0:
        delete_old_archives(archive_dir, cfg.archive_duration_days)

    mkdir_p(archive_dir)
    now = datetime.datetime.now()
    output = os.path.join(archive_dir, now.strftime('%Y%m%d-%H%M.sql.gz'))

    print >>sys.stderr, 'Archiving the current database'
    return shell(
        'mysqldump --defaults-file="%s" --databases %s | '
        'gzip > %s' % (ch_my_cnf, ' '.join(dbs_to_archive), output))

def expire_stats(cfg):
    stats_db = chdb.init_stats_db()
    with chdb.init_stats_db() as cursor, chdb.ignore_warnings():
        cursor.execute('DELETE FROM requests WHERE DATEDIFF(NOW(), ts) > %s',
                (cfg.stats_max_age_days,))

def _update_db_tools_labs(cfg):
    os.environ['CH_LANG'] = cfg.lang_code
    ch_my_cnf, wp_my_cnf = ensure_db_config(cfg)
    if cfg.archive_dir and not archive_database(ch_my_cnf, cfg):
        # Log, but don't assert, this is not fatal
        print >>sys.stderr, 'Failed to archive database!'

    expire_stats(cfg)

    # FIXME Import and calll these scripts instead of shelling out?
    def run_script(script, cmdline = '', optional = False):
        scripts_dir = os.path.dirname(os.path.realpath(__file__))
        script_path = os.path.join(scripts_dir, script)
        cmdline = ' '.join([sys.executable, script_path, cmdline])
        assert shell(cmdline) == True or optional, 'Failed at %s' % script

    unsourced = tempfile.NamedTemporaryFile()
    run_script(
        'print_unsourced_pageids_from_wikipedia.py', wp_my_cnf + ' > ' +
        unsourced.name)
    run_script('parse_live.py', unsourced.name)
    run_script('assign_categories.py')
    run_script('install_new_database.py')

def update_db_tools_labs(cfg):
    # Should match the job's name in crontab
    logfile = 'citationhunt_update_' + cfg.lang_code + '.err'
    file(logfile, 'w').close()  # truncate logfile

    try:
        _update_db_tools_labs(cfg)
    except Exception, e:
        traceback.print_exc(file = sys.stderr)
        email('Failed to build database for %s' % cfg.lang_code, logfile)
        sys.exit(1)
    email('All done for %s!' % cfg.lang_code, logfile)
    try:
        os.mkdir(cfg.log_dir)
    except Exception:
        pass
    os.rename(logfile, os.path.join(cfg.log_dir, logfile)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Update the CitationHunt databases.')
    parser.add_argument('lang_code',
        help='One of the language codes in ../config.py')
    args = parser.parse_args()

    if not (utils.running_in_tools_labs() and utils.running_in_virtualenv()):
        print >>sys.stderr, 'Not running in a virtualenv in Tools Labs!'
        sys.exit(1)

    if args.lang_code not in config.LANG_CODES_TO_LANG_NAMES:
        print >>sys.stderr, 'Invalid lang code! Use one of: ',
        print >>sys.stderr, config.LANG_CODES_TO_LANG_NAMES.keys()
        parser.print_usage()
        sys.exit(1)

    cfg = config.get_localized_config(args.lang_code)
    update_db_tools_labs(cfg)
