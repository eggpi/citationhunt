import chdb
import config
from utils import *
from common import *

from snippet_parser import CITATION_NEEDED_MARKER, REF_MARKER

import collections
import urllib
import urlparse

# the markup we're going to use for [citation needed] and <ref> tags,
# pre-marked as safe for jinja.
SUPERSCRIPT_HTML = '<sup class="superscript">[%s]</sup>'
SUPERSCRIPT_MARKUP = flask.Markup(SUPERSCRIPT_HTML)
CITATION_NEEDED_MARKUP = flask.Markup(SUPERSCRIPT_HTML)

Category = collections.namedtuple('Category', ['id', 'title'])
CATEGORY_ALL = Category('all', '')

# A class wrapping database access functions so they're easier to
# mock when testing.
class Database(object):
    @staticmethod
    def query_category_by_id(lang_code, cat_id):
        cursor = get_db(lang_code).cursor()
        with log_time('get category by id'):
            cursor.execute('''
                SELECT id, title FROM categories WHERE id = %s
            ''', (cat_id,))
            return cursor.fetchone()

    @staticmethod
    def query_snippet_by_id(lang_code, id):
        cursor = get_db(lang_code).cursor()
        with log_time('select snippet by id'):
            cursor.execute('''
                SELECT snippets.snippet, snippets.section, articles.url,
                articles.title FROM snippets, articles WHERE snippets.id = %s
                AND snippets.article_id = articles.page_id;''', (id,))
            return cursor.fetchone()

    @staticmethod
    def query_snippet_by_category(lang_code, cat_id):
        cursor = get_db(lang_code).cursor()
        with log_time('select with category'):
            cursor.execute('''
                SELECT snippets.id FROM snippets, articles_categories
                WHERE snippets.article_id = articles_categories.article_id AND
                articles_categories.category_id = %s ORDER BY RAND()
                LIMIT 1;''', (cat_id,))
            return cursor.fetchone()

    @staticmethod
    def query_random_snippet(lang_code):
        cursor = get_db(lang_code).cursor()
        cursor.execute(
            'SELECT id FROM snippets WHERE RAND() < 1e-4 LIMIT 1;')
        return cursor.fetchone()

    @staticmethod
    def query_next_id(lang_code, curr_id, cat_id):
        cursor = get_db(lang_code).cursor()

        with log_time('select next id'):
            cursor.execute('''
                SELECT next FROM snippets_links WHERE prev = %s
                AND cat_id = %s''', (curr_id, cat_id))
            return cursor.fetchone()

    @staticmethod
    def search_category(lang_code, needle, max_results):
        cursor = get_db(lang_code).cursor()

        needle = '%' + needle + '%'
        with log_time('search category'):
            cursor.execute('''
                SELECT id, title FROM categories WHERE title LIKE %s
                LIMIT %s''', (needle, max_results))
        return [{'id': row[0], 'title': row[1]} for row in cursor]

def get_category_by_id(lang_code, cat_id):
    if cat_id == CATEGORY_ALL.id:
        return CATEGORY_ALL
    c = Database.query_category_by_id(lang_code, cat_id)
    return Category(*c) if c is not None else None

def select_random_id(lang_code, cat = CATEGORY_ALL):
    ret = None
    if cat is not CATEGORY_ALL:
        ret = Database.query_snippet_by_category(lang_code, cat.id)

    if ret is None:
        # Try to pick one id at random. For small datasets, the probability
        # of getting an empty set in a query is non-negligible, so retry a
        # bunch of times as needed.
        with log_time('select without category'):
            for retry in range(1000):
                ret = Database.query_random_snippet(lang_code)
                if ret: break

    assert ret and len(ret) == 1
    return ret[0]

def select_next_id(lang_code, curr_id, cat = CATEGORY_ALL):
    if cat is not CATEGORY_ALL:
        ret = Database.query_next_id(lang_code, curr_id, cat.id)
        if ret is None:
            # curr_id doesn't belong to the category
            return None
        assert ret and len(ret) == 1
        next_id = ret[0]
    else:
        next_id = curr_id
        for i in range(3): # super paranoid :)
            next_id = select_random_id(lang_code, cat)
            if next_id != curr_id:
                break
    return next_id

def should_autofocus_category_filter(cat, request):
    return cat is CATEGORY_ALL and not request.MOBILE

@validate_lang_code
def citation_hunt(lang_code):
    id = flask.request.args.get('id')
    cat = flask.request.args.get('cat')
    cfg = config.get_localized_config(lang_code)

    lang_dir = cfg.lang_dir
    if flask.current_app.debug:
        lang_dir = flask.request.args.get('dir', lang_dir)

    if cat is not None:
        cat = get_category_by_id(lang_code, cat)
        if cat is None:
            # invalid category, normalize to "all" and try again by id
            cat = CATEGORY_ALL
            return flask.redirect(
                flask.url_for('citation_hunt',
                    lang_code = lang_code, id = id, cat = cat.id))
    else:
        cat = CATEGORY_ALL

    if id is not None:
        sinfo = Database.query_snippet_by_id(lang_code, id)
        if sinfo is None:
            # invalid id
            flask.request.cfg = cfg
            flask.abort(404)
        snippet, section, aurl, atitle = sinfo
        if cfg.html_snippet:
            snippet = flask.Markup(snippet)
        next_snippet_id = select_next_id(lang_code, id, cat)
        if next_snippet_id is None:
            # the snippet doesn't belong to the category!
            assert cat is not CATEGORY_ALL
            return flask.redirect(
                flask.url_for('citation_hunt',
                    id = id, cat = CATEGORY_ALL.id,
                    lang_code = lang_code))
        autofocus = should_autofocus_category_filter(cat, flask.request)
        article_url_path = urllib.quote(
            e(urlparse.urlparse(aurl).path.lstrip('/')))
        return flask.render_template('index.html',
            snippet = snippet, section = section, article_url = aurl,
            article_url_path = article_url_path,
            article_title = atitle, current_category = cat,
            next_snippet_id = next_snippet_id,
            cn_marker = CITATION_NEEDED_MARKER,
            cn_html = CITATION_NEEDED_MARKUP,
            ref_marker = REF_MARKER,
            ref_html = SUPERSCRIPT_MARKUP,
            config = cfg,
            lang_dir = lang_dir,
            category_filter_autofocus = autofocus)

    id = select_random_id(lang_code, cat)
    return flask.redirect(
        flask.url_for('citation_hunt',
            id = id, cat = cat.id, lang_code = lang_code))

@validate_lang_code
def search_category(lang_code):
    return flask.jsonify(
        results=Database.search_category(
            lang_code, flask.request.args.get('q'), max_results = 400))
