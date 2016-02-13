import chdb
import config

import flask

import contextlib
from datetime import datetime
import functools

def get_db(lang_code):
    localized_dbs = getattr(flask.g, '_localized_dbs', {})
    db = localized_dbs.get(lang_code, None)
    if db is None:
        db = localized_dbs[lang_code] = chdb.init_db(lang_code)
    flask.g._localized_dbs = localized_dbs
    return db

@contextlib.contextmanager
def log_time(operation):
    before = datetime.now()
    yield
    after = datetime.now()
    ms = (after - before).microseconds / 1000.
    flask.current_app.logger.debug('%s took %.2f ms', operation, ms)

def get_stats_db():
    db = getattr(flask.g, '_stats_db', None)
    if db is None:
        db = flask.g._stats_db = chdb.init_stats_db()
    return db

def validate_lang_code(handler):
    @functools.wraps(handler)
    def wrapper(lang_code = '', *args, **kwds):
        flask.request.lang_code = lang_code
        if lang_code not in config.lang_code_to_config:
            response = flask.redirect(
                flask.url_for('citation_hunt', lang_code = 'en',
                    **flask.request.args))
            if flask.request.path != '/':
                response.headers['Location'] += flask.request.path
            return response
        return handler(lang_code, *args, **kwds)
    return wrapper

