import chdb

import flask
import flask_sslify
from flask.ext.compress import Compress

import os
import contextlib
import collections
from datetime import datetime

@contextlib.contextmanager
def log_time(operation):
    before = datetime.now()
    yield
    after = datetime.now()
    ms = (after - before).microseconds / 1000.
    print '[citationhunt] %s took %.2f ms' % (operation, ms)

def get_db():
    db = getattr(flask.g, '_db', None)
    if db is None:
        db = flask.g._db = chdb.init_db()
    return db

Category = collections.namedtuple('Category', ['id', 'title'])
CATEGORY_ALL = Category('all', '')
def get_categories(include_default = True):
    categories = getattr(flask.g, '_categories', None)
    if categories is None:
        cursor = get_db().cursor()
        cursor.execute('''
            SELECT id, title FROM categories WHERE id != "unassigned"
            ORDER BY title;
        ''')
        categories = [CATEGORY_ALL] + [Category(*row) for row in cursor]
        flask.g._categories = categories
    return categories if include_default else categories[1:]

def get_category_by_id(catid, default = None):
    for c in get_categories():
        if catid == c.id:
            return c
    return default

def select_snippet_by_id(id):
    # The query below may match snippets with unassigned categories. That's
    # fine, we don't display the current category in the UI anyway.
    cursor = get_db().cursor()
    with log_time('select snippet by id'):
        cursor.execute('''
            SELECT snippets.snippet, snippets.section, articles.url,
            articles.title FROM snippets, articles WHERE snippets.id = ? AND
            snippets.article_id = articles.page_id;''', (id,))
        ret = cursor.fetchone()
    return ret

def select_random_id(cat = CATEGORY_ALL):
    cursor = get_db().cursor()

    ret = None
    if cat is not CATEGORY_ALL:
        with log_time('select with category'):
            cursor.execute('''
                SELECT snippets.id FROM snippets, articles
                WHERE snippets.article_id = articles.page_id
                AND articles.category_id = ? ORDER BY RANDOM()
                LIMIT 1;''', (cat.id,))
            ret = cursor.fetchone()

    if ret is None:
        with log_time('select without category'):
            cursor.execute('''
                SELECT id FROM snippets WHERE RANDOM() % 10000 = 0 LIMIT 1;''')
            ret = cursor.fetchone()

    assert ret and len(ret) == 1
    return ret[0]

app = flask.Flask(__name__)
flask_sslify.SSLify(app, permanent = True)
Compress(app)

@app.route('/')
def citation_hunt():
    id = flask.request.args.get('id')
    cat = flask.request.args.get('cat')

    if cat is not None:
        cat = get_category_by_id(cat)
        if cat is None:
            # invalid category, normalize to "all" and try again by id
            cat = CATEGORY_ALL
            return flask.redirect(
                flask.url_for('citation_hunt', id = id, cat = cat.id))
    else:
        cat = CATEGORY_ALL

    if id is not None:
        # pick snippet by id and just echo back the category, even
        # if the snippet doesn't belong to it.
        sinfo = select_snippet_by_id(id)
        if sinfo is None:
            # invalid id
            flask.abort(404)
        snippet, section, aurl, atitle = sinfo
        return flask.render_template('index.html',
            snippet = snippet, section = section, article_url = aurl,
            article_title = atitle, current_category = cat)

    id = select_random_id(cat)
    return flask.redirect(
        flask.url_for('citation_hunt', id = id, cat = cat.id))

@app.route('/categories.html')
def categories_html():
    return flask.render_template('categories.html',
        categories = get_categories(include_default = False));

@app.after_request
def add_cache_header(response):
    if response.status_code != 302 and response.cache_control.max_age is None:
        response.cache_control.public = True
        response.cache_control.max_age = 3 * 24 * 60 * 60
    return response

@app.teardown_appcontext
def close_db(exception):
    db = getattr(flask.g, '_db', None)
    if db is not None:
        db.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = 'DEBUG' in os.environ
    app.run(host = '0.0.0.0', port = port, debug = debug)
