import sqlite3

DB_FILENAME = 'citationhunt.sqlite3'

def init_db():
    return sqlite3.connect(DB_FILENAME)

def reset_db():
    db = init_db()

    with db:
        db.execute('''
            DROP TABLE categories
        ''')
        db.execute('''
            DROP TABLE articles
        ''')
        db.execute('''
            DROP TABLE snippets
        ''')
        db.execute('''
            DROP TABLE articles_categories
        ''')
        db.execute('''
            CREATE TABLE categories (id TEXT PRIMARY KEY, title TEXT)
        ''')
        db.execute('''
            INSERT INTO categories VALUES ("unassigned", "unassigned")
        ''')
        db.execute('''
            CREATE TABLE articles_categories (article_id TEXT, category_id TEXT,
            FOREIGN KEY(article_id) REFERENCES articles(page_id)
            ON DELETE CASCADE,
            FOREIGN KEY(category_id) REFERENCES categories(id)
            ON DELETE CASCADE)
        ''')
        db.execute('''
            CREATE TABLE articles (page_id TEXT PRIMARY KEY, url TEXT,
            title TEXT)
        ''')
        db.execute('''
            CREATE TABLE snippets (id TEXT PRIMARY KEY, snippet TEXT,
            section TEXT, article_id TEXT, FOREIGN KEY(article_id)
            REFERENCES articles(page_id) ON DELETE CASCADE)
        ''')

    return db

def create_indices():
    db = init_db()

    db.execute('''CREATE INDEX IF NOT EXISTS snippets_articles
        ON snippets(article_id);''')
