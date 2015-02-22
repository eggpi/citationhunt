import sqlite3

def init_db():
    db = sqlite3.connect('citationhunt.sqlite3')

    with db:
        db.execute('''
            DROP TABLE IF EXISTS cn
        ''')
        db.execute('''
            DROP TABLE IF EXISTS cat
        ''')
        db.execute('''
            DROP TABLE IF EXISTS cn_cat
        ''')
        db.execute('''
            CREATE TABLE cn (id TEXT PRIMARY KEY, snippet TEXT, url TEXT,
            title TEXT)
        ''')
        db.execute('''
            CREATE TABLE cat (id TEXT PRIMARY KEY, name TEXT);
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS cn_cat (snippet_id TEXT, cat_id TEXT,
            FOREIGN KEY(snippet_id) REFERENCES cn(id), FOREIGN KEY(cat_id)
            REFERENCES cat(id))''')

    return db
