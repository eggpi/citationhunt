import sqlite3

def init_db():
    db = sqlite3.connect('citationhunt.sqlite3')
    cursor = db.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cn (id text primary key, snippet text, url text, title text)
    ''')

    return db
