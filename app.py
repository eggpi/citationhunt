import chdb

import flask

import os

def get_db():
    db = getattr(flask.g, '_db', None)
    if db is None:
        db = flask.g._db = chdb.init_db()
    return db

def select_snippet_by_id(id):
    cursor = get_db().cursor()
    # FIXME LIMIT 1 because we have duplicates
    cursor.execute('''
        SELECT snippet, url, title FROM cn WHERE id = ? LIMIT 1;''', (id,))
    return cursor.fetchone()

def select_random_id():
    cursor = get_db().cursor()
    cursor.execute('''
        SELECT id FROM cn ORDER BY RANDOM() LIMIT 1;''')
    return cursor.fetchone()[0]

app = flask.Flask(__name__)

@app.route('/')
def citation_hunt():
    id = flask.request.args.get('id')
    if id is None:
        id = select_random_id()
        return flask.redirect(flask.url_for('citation_hunt', id = id))

    s, u, t = select_snippet_by_id(id)
    return flask.render_template('index.html', snippet = s, url = u, title = t)

@app.teardown_appcontext
def close_db(exception):
    db = getattr(flask.g, '_db', None)
    if db is not None:
        db.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host = '0.0.0.0', port = port)
