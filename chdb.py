import config
import utils

import MySQLdb

import contextlib
import os
import time
import warnings

REPLICA_MY_CNF = os.getenv(
    'REPLICA_MY_CNF', os.path.expanduser('~/replica.my.cnf'))
TOOLS_LABS_CH_MYSQL_HOST = 'tools.db.svc.eqiad.wmflabs'

class _RetryingConnection(object):
    '''
    Wraps a MySQLdb connection, handling retries as needed.
    '''

    def __init__(self, connect, sleep = time.sleep):
        self._connect = connect
        self._sleep = sleep
        self._do_connect()

    def _do_connect(self):
        self.conn = self._connect()
        self.conn.ping(True) # set the reconnect flag

    def execute_with_retry(self, operations, *args, **kwds):
        max_retries = 5
        for retry in range(max_retries):
            try:
                with self.conn as cursor:
                    return operations(cursor, *args, **kwds)
            except MySQLdb.OperationalError:
                if retry == max_retries - 1:
                    raise
                else:
                    self._sleep(2 ** retry)
                    self._do_connect()
            else:
                break

    def execute_with_retry_s(self, sql, *args):
        def operations(cursor, sql, *args):
            cursor.execute(sql, args)
            if cursor.rowcount > 0:
                return cursor.fetchall()
            return None
        return self.execute_with_retry(operations, sql, *args)

    # https://stackoverflow.com/questions/4146095/ (sigh)
    def __enter__(self):
        return self.conn.__enter__()

    def __exit__(self, *args):
        return self.conn.__exit__(*args)

    def __getattr__(self, name):
        return getattr(self.conn, name)

@contextlib.contextmanager
def ignore_warnings():
    warnings.filterwarnings('ignore', category = MySQLdb.Warning)
    yield
    warnings.resetwarnings()

def _connect(**kwds):
    return MySQLdb.connect(charset = 'utf8mb4', **kwds)

def _connect_to_ch_mysql():
    kwds = {'read_default_file': REPLICA_MY_CNF}
    if utils.running_in_tools_labs():
        kwds['host'] = TOOLS_LABS_CH_MYSQL_HOST
    return _connect(**kwds)

def _connect_to_wp_mysql(cfg):
    kwds = {'read_default_file': REPLICA_MY_CNF}
    if utils.running_in_tools_labs():
        # Get the project database name (and ultimately the database server's
        # hostname) from the name of the database we want, as per:
        # https://wikitech.wikimedia.org/wiki/Help:Tool_Labs/Database#Naming_conventions
        xxwiki = cfg.database.replace('_p', '')
        kwds['host'] = '%s.analytics.db.svc.eqiad.wmflabs' % xxwiki
    return _connect(**kwds)

def _make_tools_labs_dbname(cursor, database, lang_code):
    cursor.execute("SELECT SUBSTRING_INDEX(USER(), '@', 1)")
    user = cursor.fetchone()[0]
    return '%s__%s_%s' % (user, database, lang_code)

def _use(cursor, database, lang_code):
    cursor.execute('USE %s' % _make_tools_labs_dbname(
        cursor, database, lang_code))

# Methods that connect and help introspect into our databases. They do not
# create databases or tables, so are suitable for use in the serving path
# (see https://phabricator.wikimedia.org/T216213).

def get_table_name(db, database, table):
    cfg = config.get_localized_config()
    return _make_tools_labs_dbname(
        db.cursor(), database, cfg.lang_code) + '.' + table

def init_db(lang_code):
    def connect_and_initialize():
        db = _connect_to_ch_mysql()
        _use(db.cursor(), 'citationhunt', lang_code)
        return db
    return _RetryingConnection(connect_and_initialize)

def init_scratch_db():
    cfg = config.get_localized_config()
    def connect_and_initialize():
        db = _connect_to_ch_mysql()
        _use(db.cursor(), 'scratch', cfg.lang_code)
        return db
    return _RetryingConnection(connect_and_initialize)

def init_stats_db():
    def connect_and_initialize():
        db = _connect_to_ch_mysql()
        _use(db.cursor(), 'stats', 'global')
        return db
    return _RetryingConnection(connect_and_initialize)

def init_wp_replica_db(lang_code):
    cfg = config.get_localized_config(lang_code)
    def connect_and_initialize():
        db = _connect_to_wp_mysql(cfg)
        with db as cursor:
            cursor.execute('USE ' + cfg.database)
        return db
    return _RetryingConnection(connect_and_initialize)

def get_en_projectindex_database_name():
    return 's52475__wpx_p'

# Methods for use in batch scripts, not the serving frontend. These set up the
# databases, help populate the scratch database and swap it with the serving
# database.

def _create_citationhunt_tables(cfg, cursor):
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (id VARCHAR(128) PRIMARY KEY,
        title VARCHAR(255)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')
    cursor.execute('''
        INSERT IGNORE INTO categories VALUES("unassigned", "unassigned")
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS intersections (
        id VARCHAR(128) PRIMARY KEY, expiration DATETIME)
        ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (page_id INT(8) UNSIGNED
        PRIMARY KEY, url VARCHAR(512), title VARCHAR(512))
        ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles_categories (
        article_id INT(8) UNSIGNED, category_id VARCHAR(128),
        FOREIGN KEY(article_id) REFERENCES articles(page_id)
        ON DELETE CASCADE,
        FOREIGN KEY(category_id) REFERENCES categories(id)
        ON DELETE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles_intersections (
        article_id INT(8) UNSIGNED, inter_id VARCHAR(128),
        PRIMARY KEY(article_id, inter_id),
        FOREIGN KEY(article_id) REFERENCES articles(page_id)
        ON DELETE CASCADE,
        FOREIGN KEY(inter_id) REFERENCES intersections(id)
        ON DELETE CASCADE)
        ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS category_article_count (
        category_id VARCHAR(128), article_count INT(8) UNSIGNED,
        FOREIGN KEY(category_id) REFERENCES categories(id)
        ON DELETE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS snippets (id VARCHAR(128) PRIMARY KEY,
        snippet VARCHAR(%s), section VARCHAR(768), article_id INT(8)
        UNSIGNED, FOREIGN KEY(article_id) REFERENCES articles(page_id)
        ON DELETE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''', (cfg.snippet_max_size * 10,))
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS snippets_links (prev VARCHAR(128),
        next VARCHAR(128), cat_id VARCHAR(128), inter_id VARCHAR(128),
        FOREIGN KEY(prev) REFERENCES snippets(id) ON DELETE CASCADE,
        FOREIGN KEY(next) REFERENCES snippets(id) ON DELETE CASCADE,
        FOREIGN KEY(cat_id) REFERENCES categories(id) ON DELETE CASCADE,
        FOREIGN KEY(inter_id) REFERENCES intersections(id) ON DELETE CASCADE)
        ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')

def _create_stats_tables(cfg, cursor):
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
        ts DATETIME, lang_code VARCHAR(10), snippet_id VARCHAR(128),
        category_id VARCHAR(128), url VARCHAR(768), prefetch BOOLEAN,
        status_code INTEGER, referrer VARCHAR(128))
        ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fixed (
        clicked_ts DATETIME, snippet_id VARCHAR(128) UNIQUE,
        lang_code VARCHAR(10), rev_id INT(8) DEFAULT -1)
        ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')
    # Create per-language views for convenience
    for lang_code in cfg.lang_codes_to_lang_names:
        cursor.execute('''
            CREATE OR REPLACE VIEW requests_''' + lang_code +
            ''' AS SELECT * FROM requests WHERE lang_code = %s
        ''', (lang_code,))
        cursor.execute('''
            CREATE OR REPLACE VIEW fixed_''' + lang_code +
            ''' AS SELECT * FROM fixed WHERE lang_code = %s
        ''', (lang_code,))

def initialize_all_databases():
    def _do_create_database(cursor, database, lang_code):
        dbname = _make_tools_labs_dbname(cursor, database, lang_code)
        cursor.execute('SET SESSION sql_mode = ""')
        cursor.execute(
            'CREATE DATABASE IF NOT EXISTS %s '
            'CHARACTER SET utf8mb4' % dbname)
    cfg = config.get_localized_config()
    db = _RetryingConnection(_connect_to_ch_mysql)
    with db as cursor, ignore_warnings():
        cursor.execute('DROP DATABASE IF EXISTS ' + _make_tools_labs_dbname(
            cursor, 'scratch', cfg.lang_code))
        for database in ['citationhunt', 'scratch', 'stats']:
            _do_create_database(cursor, database,
                cfg.lang_code if database != 'stats' else 'global')
        _use(cursor, 'scratch', cfg.lang_code)
        _create_citationhunt_tables(cfg, cursor)
        _use(cursor, 'citationhunt', cfg.lang_code)
        _create_citationhunt_tables(cfg, cursor)
        _use(cursor, 'stats', 'global')
        _create_stats_tables(cfg, cursor)

def install_scratch_db():
    cfg = config.get_localized_config()
    with init_db(cfg.lang_code) as cursor:
        chname = _make_tools_labs_dbname(cursor, 'citationhunt', cfg.lang_code)
        scname = _make_tools_labs_dbname(cursor, 'scratch', cfg.lang_code)
        # generate a sql query that will atomically swap tables in
        # 'citationhunt' and 'scratch'. Modified from:
        # http://blog.shlomoid.com/2010/02/emulating-missing-rename-database.html
        cursor.execute('''SET group_concat_max_len = 2048;''')
        cursor.execute('''
            SELECT CONCAT('RENAME TABLE ',
            GROUP_CONCAT('%s.', table_name,
            ' TO ', table_schema, '.old_', table_name, ', ',
            table_schema, '.', table_name, ' TO ', '%s.', table_name),';')
            FROM information_schema.TABLES WHERE table_schema = '%s'
            GROUP BY table_schema;
        ''' % (chname, chname, scname))

        rename_stmt = cursor.fetchone()[0]
        cursor.execute(rename_stmt)
        cursor.execute('DROP DATABASE ' + scname)
