import chdb
import config
import chstrings

import flask

import contextlib
from datetime import datetime
from dataclasses import dataclass
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

@dataclass
class AcceptLanguageEntry:
    base_tag: str
    lang_tag: str
    weight: float

def parse_accept_language_header(accept_language_header):
    results = []
    for full_tag in accept_language_header.split(','):
        weight = 0.0
        if ';' in full_tag:
            full_tag, weight = full_tag.split(';', 1)
        base_tag = full_tag
        if '-' in full_tag:
            base_tag = full_tag.split('-', 1)[0]
        results.append(AcceptLanguageEntry(
            base_tag.strip(), full_tag.strip(), weight))
    return results

def find_default_lang_code_for_request(accept_language):
    lang_tags_in_header = []
    for al in accept_language:
        # We ignore the weight, but try to match the full lang_tag before the
        # less specific base_tag.
        lang_tags_in_header.extend([al.lang_tag, al.base_tag])
    for lang_tag in lang_tags_in_header:
        for lcode, ltags in list(config.LANG_CODES_TO_ACCEPT_LANGUAGE.items()):
            if lang_tag in ltags or lcode == lang_tag:
                return lcode
    return 'en'

# A lang_code in the config identifies a set of config keys, but
# it is orthogonal to the set of strings we'll use in the UI. Try
# to determine the strings here.
def load_strings_for_request(lang_code, cfg, accept_language):
    for al in accept_language:
        lang_tag_matches_config = (
            al.base_tag == lang_code or
            al.lang_tag in cfg.accept_language or
            al.base_tag in cfg.accept_language
        )
        if not lang_tag_matches_config:
            continue

        # Do we have strings for the full tag?
        strings = chstrings.get_localized_strings(cfg, al.lang_tag)
        if strings:
            return al.lang_tag, strings
        # Maybe just the base tag?
        strings = chstrings.get_localized_strings(cfg, al.base_tag)
        if strings:
            return al.base_tag, strings

    fallback = lang_code
    if cfg.accept_language:
        fallback = cfg.accept_language[-1]
    return fallback, chstrings.get_localized_strings(cfg, fallback)

def validate_lang_code(handler):
    @functools.wraps(handler)
    def wrapper(lang_code = '', *args, **kwds):
        accept_language = parse_accept_language_header(
            flask.request.headers.get('Accept-Language', ''))

        lang_code = lang_code.lower()
        if not lang_code:
            return redirect_to_lang_code(
                find_default_lang_code_for_request(accept_language))

        flask.g._lang_code = lang_code
        if lang_code not in config.LANG_CODES_TO_LANG_NAMES:
            return redirect_to_lang_code('en')

        flask.g._cfg = config.get_localized_config(lang_code, api = False)
        if flask.current_app.debug and 'locale' in flask.request.args:
            flask.g._strings = chstrings.get_localized_strings(
                flask.g._cfg, flask.request.args['locale'])
        else:
            flask.g._lang_tag, flask.g._strings = load_strings_for_request(
                lang_code, flask.g._cfg, accept_language)
        if not flask.g._strings:
            # Shouldn't really happen, this means we have a misconfigured
            # language that has a config entry but no strings.
            flask.request.path = ''
            return redirect_to_lang_code('en')
        return handler(lang_code, *args, **kwds)
    return wrapper

