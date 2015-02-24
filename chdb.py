import sqlite3

def init_db():
    db = sqlite3.connect('citationhunt.sqlite3')

    with db:
        db.execute('''
            DROP TABLE IF EXISTS categories
        ''')
        db.execute('''
            DROP TABLE IF EXISTS articles
        ''')
        db.execute('''
            DROP TABLE IF EXISTS snippets
        ''')
        db.execute('''
            CREATE TABLE categories (id TEXT PRIMARY KEY, title TEXT)
        ''')
        db.execute('''
            INSERT INTO categories VALUES ("unassigned", "unassigned")
        ''')
        db.execute('''
            CREATE TABLE articles (page_id TEXT PRIMARY KEY, url TEXT,
            title TEXT, category_id TEXT,
            FOREIGN KEY(category_id) REFERENCES categories(id)
            ON DELETE CASCADE)
        ''')
        db.execute('''
            CREATE TABLE snippets (id TEXT PRIMARY KEY, snippet TEXT,
            article_id TEXT, FOREIGN KEY(article_id)
            REFERENCES articles(page_id) ON DELETE CASCADE)
        ''')

    return db
