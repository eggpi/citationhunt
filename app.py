import chdb
import config
import handlers

import flask
import flask_sslify
from flask.ext.compress import Compress
from flask.ext.mobility import Mobility

import os

# Cache duration for snippets.
# Since each page contains a link to the next one, even when no category is
# selected, we risk users getting trapped circling among their cached pages
# sometimes. We do depend on caching for prefetching to work, but let's do
# it for only a short period to be safe.
# An alternative would be to never cache when no category is selected UNLESS
# when prefetching, but that's a bit more complex.
CACHE_DURATION_SNIPPET = 60

# Cache duration for things that get regenerated along with database updates,
# such as the list of categories.
CACHE_DURATION_SEMI_STATIC = 3 * 60 * 60

app = flask.Flask(__name__)
Compress(app)
debug = 'DEBUG' in os.environ
if not debug:
    flask_sslify.SSLify(app, permanent = True)
Mobility(app)

@app.route('/')
@handlers.validate_lang_code
def index(lang_code):
    pass # nothing to do but validate lang_code

app.add_url_rule('/<lang_code>', view_func = handlers.citation_hunt)
app.add_url_rule('/<lang_code>/stats.html', view_func = handlers.stats)

@app.route('/<lang_code>/categories.html')
@handlers.validate_lang_code
def categories_html(lang_code):
    response = flask.make_response(
        flask.render_template('categories.html',
            categories = handlers.get_categories(
                lang_code, include_default = False)))
    response.cache_control.max_age = CACHE_DURATION_SEMI_STATIC
    return response

@app.after_request
def add_cache_header(response):
    if response.status_code == 302:
        response.cache_control.no_cache = True
        response.cache_control.no_store = True
        return response

    if response.status_code != 200:
        return response

    response.cache_control.public = True
    if response.cache_control.max_age is not None:
        return response

    response.cache_control.max_age = CACHE_DURATION_SNIPPET
    return response

@app.after_request
def log_request(response):
    lang_code = getattr(flask.request, 'lang_code', None)
    id = flask.request.args.get('id')
    cat = flask.request.args.get('cat')
    url = flask.request.url
    prefetch = False
    prefetch = (flask.request.headers.get('purpose') == 'prefetch' or
                flask.request.headers.get('X-Moz') == 'prefetch')
    user_agent = flask.request.headers.get('User-Agent', 'NULL')
    referrer = flask.request.referrer
    status_code = response.status_code

    with handlers.get_stats_db() as cursor, chdb.ignore_warnings():
        cursor.execute('INSERT INTO requests VALUES '
            '(NOW(), %s, %s, %s, %s, %s, %s, %s, %s)',
            (lang_code, id, cat, url, prefetch, user_agent,
             status_code, referrer))
    return response

@app.teardown_appcontext
def close_db(exception):
    db = getattr(flask.g, '_db', None)
    if db is not None:
        db.close()

if '404' not in config.get_localized_config('en').flagged_off:
    @app.errorhandler(404)
    def page_not_found(e):
        if not hasattr(flask.request, 'cfg'):
            flask.request.cfg = config.get_localized_config('en')
        return flask.render_template(
            '404.html', config = flask.request.cfg), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host = '0.0.0.0', port = port, debug = debug)
