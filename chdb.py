import MySQLdb

import warnings
import os.path as op
import contextlib

ch_my_cnf = op.join(op.dirname(op.realpath(__file__)), 'ch.my.cnf')
wp_my_cnf = op.join(op.dirname(op.realpath(__file__)), 'wp.my.cnf')

class RetryingConnection(object):
    '''
    Wraps a MySQLdb connection, handling retries as needed.
    '''

    def __init__(self, connect):
        self._connect = connect
        self._do_connect()

    def _do_connect(self):
        self.conn = self._connect()
        self.conn.ping(True) # set the reconnect flag

    def execute_with_retry(self, operations):
        max_retries = 5
        for retry in range(max_retries):
            try:
                with self.conn as cursor:
                    operations(cursor)
            except MySQLdb.OperationalError:
                if retry == max_retries - 1:
                    raise
                else:
                    self._do_connect()
            else:
                break

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

def _connect(config_file, database = ''):
    return MySQLdb.connect(charset = 'utf8mb4', read_default_file = config_file)

def _make_tools_labs_dbname(db, database):
    cursor = db.cursor()
    cursor.execute("SELECT SUBSTRING_INDEX(USER(), '@', 1)")
    user = cursor.fetchone()[0]
    return '%s__%s' % (user, database)

def _ensure_database(db, database):
    with db as cursor:
        dbname = _make_tools_labs_dbname(db, database)
        with ignore_warnings():
            cursor.execute(
                'CREATE DATABASE IF NOT EXISTS %s CHARACTER SET utf8mb4' % dbname)
        cursor.execute('USE %s' % dbname)

def init_db():
    def connect_and_initialize():
        db = _connect(ch_my_cnf)
        _ensure_database(db, 'citationhunt')
        return db
    return RetryingConnection(connect_and_initialize)

def init_scratch_db():
    def connect_and_initialize():
        db = _connect(ch_my_cnf)
        _ensure_database(db, 'scratch')
        return db
    return RetryingConnection(connect_and_initialize)

def init_wp_replica_db():
    def connect_and_initialize():
        db = _connect(wp_my_cnf)
        with db as cursor:
            cursor.execute('USE enwiki_p')
        return db
    return RetryingConnection(connect_and_initialize)

def reset_scratch_db():
    db = init_db()
    with db as cursor:
        dbname = _make_tools_labs_dbname(db, 'scratch')
        with ignore_warnings():
            cursor.execute('DROP DATABASE IF EXISTS ' + dbname)
        cursor.execute('CREATE DATABASE %s CHARACTER SET utf8mb4' % dbname)
        cursor.execute('USE ' + dbname)
    create_tables(db)
    return db

def install_scratch_db():
    db = init_db()
    # ensure citationhunt is populated with tables
    create_tables(db)

    chname = _make_tools_labs_dbname(db, 'citationhunt')
    scname = _make_tools_labs_dbname(db, 'scratch')
    with db as cursor:
        # generate a sql query that will atomically swap tables in
        # 'citationhunt' and 'scratch'. Modified from:
        # http://blog.shlomoid.com/2010/02/emulating-missing-rename-database.html
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

def create_tables(db):
    with db as cursor, ignore_warnings():
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (id VARCHAR(128) PRIMARY KEY,
            title VARCHAR(255)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        cursor.execute('''
            INSERT IGNORE INTO categories VALUES("unassigned", "unassigned")
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (page_id VARCHAR(128)
            PRIMARY KEY, url VARCHAR(512), title VARCHAR(512))
            ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles_categories (
            article_id VARCHAR(128), category_id VARCHAR(128),
            FOREIGN KEY(article_id) REFERENCES articles(page_id)
            ON DELETE CASCADE,
            FOREIGN KEY(category_id) REFERENCES categories(id)
            ON DELETE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS snippets (id VARCHAR(128) PRIMARY KEY,
            snippet VARCHAR(512), section VARCHAR(512), article_id VARCHAR(128),
            FOREIGN KEY(article_id) REFERENCES articles(page_id)
            ON DELETE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS snippets_links (prev VARCHAR(128),
            next VARCHAR(128), cat_id VARCHAR(128),
            FOREIGN KEY(prev) REFERENCES snippets(id) ON DELETE CASCADE,
            FOREIGN KEY(next) REFERENCES snippets(id) ON DELETE CASCADE,
            FOREIGN KEY(cat_id) REFERENCES categories(id) ON DELETE CASCADE)
            ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
