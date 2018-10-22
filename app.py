import chdb
import chstrings
import config
import handlers
import utils

import flask
import flask_sslify
from flask.ext.compress import Compress

import os
import urllib
import urlparse
import traceback
import logging.handlers

# Cache duration for snippets.
# Since each page contains a link to the next one, even when no category is
# selected, we risk users getting trapped circling among their cached pages
# sometimes. We do depend on caching for prefetching to work, but let's do
# it for only a short period to be safe.
# An alternative would be to never cache when no category is selected UNLESS
# when prefetching, but that's a bit more complex.
CACHE_DURATION_SNIPPET = 30

global_config = config.get_global_config()

app = flask.Flask(__name__)
Compress(app)
debug = 'DEBUG' in os.environ
if not debug:
    flask_sslify.SSLify(app, permanent = True)

@app.route('/')
@handlers.validate_lang_code
def index(lang_code):
    pass # nothing to do but validate lang_code

app.add_url_rule('/<lang_code>', view_func = handlers.citation_hunt,
    strict_slashes = False)
app.add_url_rule('/<lang_code>/stats.html', view_func = handlers.stats)
if 'stats' not in global_config.flagged_off:
    app.after_request(handlers.log_request)
app.add_url_rule('/<lang_code>/search/category',
    view_func = handlers.search_category)
app.add_url_rule('/<lang_code>/fixed', view_func = handlers.fixed)
app.add_url_rule('/<lang_code>/leaderboard.html',
    view_func = handlers.leaderboard)
app.add_url_rule('/<lang_code>/intersection',
    view_func = handlers.create_intersection, methods = ['POST'])

if not debug:
    log_dir = global_config.log_dir
    utils.mkdir_p(log_dir)
    log_file = os.path.join(log_dir, 'ch.log')
    log_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes = 1024 * 1024, encoding = 'utf-8')
    log_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [%(pathname)s:%(lineno)d]'))
    log_handler.setLevel(logging.INFO)
    app.logger.addHandler(log_handler)
    app.logger.setLevel(logging.INFO)
    print 'writing server logs to %s' % log_file

@app.before_first_request
def log_hello():
    app.logger.info('logging says hello!')

@app.route('/<lang_code>/redirect')
@handlers.validate_lang_code
def redirect(lang_code):
    to = urllib.unquote(flask.request.args.get('to', ''))
    cfg = config.get_localized_config(lang_code)
    return flask.redirect(
        urlparse.urljoin('https://' + cfg.wikipedia_domain, to))

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

@app.errorhandler(404)
def page_not_found(e):
    if hasattr(flask.g, '_cfg'):
        cfg = flask.g._cfg
    else:
        cfg = config.get_localized_config('en')
    if hasattr(flask.g, '_strings'):
        lang_tag = flask.g._lang_tag
        strings = flask.g._strings
    else:
        lang_tag = 'en'
        strings = chstrings.get_localized_strings(cfg, 'en')
    return flask.render_template(
        '404.html', config = cfg,
        lang_tag = lang_tag,
        lang_dir = cfg.lang_dir, strings = strings), 404

@app.errorhandler(500)
def internal_server_error(e):
    app.logger.error(traceback.format_exc())
    response = flask.Response()
    response.status_code = 500
    if 'stats' not in global_config.flagged_off:
        handlers.log_request(response)
    return '<h1>Internal Error</h1><p>Sorry :(</p>', 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host = '0.0.0.0', port = port, debug = debug, threaded = True)
