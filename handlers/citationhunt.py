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
    def query_categories(lang_code):
        cursor = get_db(lang_code).cursor()
        cursor.execute('''
            SELECT id, title FROM categories WHERE id != "unassigned"
            ORDER BY title;
        ''')
        return list(cursor)

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
    def query_random_snippet(lang_code, p):
        cursor = get_db(lang_code).cursor()
        cursor.execute(
            'SELECT id FROM snippets WHERE RAND() < %s LIMIT 1;', (p,))
        return cursor.fetchone()

    @staticmethod
    def query_next_id(lang_code, curr_id, cat_id):
        cursor = get_db(lang_code).cursor()

        with log_time('select next id'):
            cursor.execute('''
                SELECT next FROM snippets_links WHERE prev = %s
                AND cat_id = %s''', (curr_id, cat_id))
            return cursor.fetchone()

def get_categories(lang_code, include_default = True):
    categories = getattr(flask.g, '_categories', None)
    if categories is None:
        categories = [
            CATEGORY_ALL
        ] + [Category(*row) for row in Database.query_categories(lang_code)]
        flask.g._categories = categories
    return categories if include_default else categories[1:]

def get_category_by_id(lang_code, catid, default = None):
    for c in get_categories(lang_code):
        if catid == c.id:
            return c
    return default

def select_random_id(lang_code, cat = CATEGORY_ALL):
    ret = None
    if cat is not CATEGORY_ALL:
        ret = Database.query_snippet_by_category(lang_code, cat.id)

    if ret is None:
        # Try to pick one id at random. For small datasets, the probability
        # of getting an empty set in a query is non-negligible, so retry a
        # bunch of times as needed.
        p = '1e-4' if not flask.current_app.debug else '1e-2'
        with log_time('select without category'):
            for retry in range(1000):
                ret = Database.query_random_snippet(lang_code, p)
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
