import sqlite3

def init_db():
    db = sqlite3.connect('citationhunt.sqlite3')
    cursor = db.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cn (id TEXT PRIMARY KEY, snippet TEXT, url TEXT, title TEXT)
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cat (name TEXT, id TEXT PRIMARY KEY);
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cn_cat (snippet_id TEXT, cat_id TEXT,
        FOREIGN KEY(snippet_id) REFERENCES cn(id), FOREIGN KEY(cat_id)
        REFERENCES cat(id))''')

    return db
