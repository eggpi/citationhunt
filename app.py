import chdb

import flask

import os

def get_db():
    db = getattr(flask.g, '_db', None)
    if db is None:
        db = flask.g._db = chdb.init_db()
    return db

def select_random_snippet():
    cursor = get_db().cursor()
    cursor.execute('''
        SELECT snippet, url, title FROM cn ORDER BY RANDOM() LIMIT 1;''')
    return cursor.fetchone()

app = flask.Flask(__name__)

@app.route('/')
def citation_hunt():
    s, u, t = select_random_snippet()
    return flask.render_template('index.html', snippet = s, url = u, title = t)

@app.teardown_appcontext
def close_db(exception):
    db = getattr(flask.g, '_db', None)
    if db is not None:
        db.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host = '0.0.0.0', port = port)
