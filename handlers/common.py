import chdb
import config
import chstrings

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

def redirect_to_lang_code(lang_code):
    response = flask.redirect(
        flask.url_for('citation_hunt', lang_code = lang_code,
            **flask.request.args))
    if flask.request.path != '/':
        response.headers['Location'] += flask.request.path
    return response

def find_default_lang_code_for_request(accept_language_hdr):
    lang_tags_in_header = [
        l.split(';', 1)[0]
        for l in accept_language_hdr.split(',')
    ] # en-GB, en;q=0.5, es-AR;q=0.3 -> [en-GB, en, es-AR]
    for lang_tag in lang_tags_in_header:
        for lcode, ltags in list(config.LANG_CODES_TO_ACCEPT_LANGUAGE.items()):
            if lang_tag in ltags or lcode == lang_tag:
                return lcode
    return 'en'

# A lang_code in the config identifies a set of config keys, but
# it is orthogonal to the set of strings we'll use in the UI. Try
# to determine the strings here.
def load_strings_for_request(lang_code, cfg, accept_language_hdr):
    header_locales = accept_language_hdr.split(',')
    for l in header_locales:
        lang_tag = l.split(';', 1)[0]  # drop weight, if any
        lang = l.split('-', 1)[0] # en-GB -> en

        lang_tag_matches_config = (
            lang == lang_code or
            lang_tag in cfg.accept_language or
            lang in cfg.accept_language
        )
        if not lang_tag_matches_config:
            continue

        # Do we have strings for the full tag?
        strings = chstrings.get_localized_strings(cfg, lang_tag)
        if strings:
            return lang_tag, strings
        # Maybe just the lang?
        strings = chstrings.get_localized_strings(cfg, lang)
        if strings:
            return lang, strings

    fallback = lang_code
    if cfg.accept_language:
        fallback = cfg.accept_language[-1]
    return fallback, chstrings.get_localized_strings(cfg, fallback)

def validate_lang_code(handler):
    @functools.wraps(handler)
    def wrapper(lang_code = '', *args, **kwds):
        accept_language_hdr = flask.request.headers.get('Accept-Language', '')
        lang_code = lang_code.lower()
        if not lang_code:
            return redirect_to_lang_code(
                find_default_lang_code_for_request(accept_language_hdr))

        flask.g._lang_code = lang_code
        if lang_code not in config.LANG_CODES_TO_LANG_NAMES:
            return redirect_to_lang_code('en')

        flask.g._cfg = config.get_localized_config(lang_code, api = False)
        if flask.current_app.debug and 'locale' in flask.request.args:
            flask.g._strings = chstrings.get_localized_strings(
                flask.g._cfg, flask.request.args['locale'])
        else:
            flask.g._lang_tag, flask.g._strings = load_strings_for_request(
                lang_code, flask.g._cfg, accept_language_hdr)
        if not flask.g._strings:
            # Shouldn't really happen, this means we have a misconfigured
            # language that has a config entry but no locales in the translation
            # files.
            return redirect_to_lang_code('en')
        return handler(lang_code, *args, **kwds)
    return wrapper

