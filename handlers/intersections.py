import chdb
import config
import database
from utils import *
from common import *

import requests
import yamwapi as mwapi

# https://www.mediawiki.org/wiki/API:Query#Specifying_pages
PAGE_TITLES_PER_API_REQUEST = 50

# do a little basic type checking
def validate_request_json(request):
    if not isinstance(request, dict):
        raise TypeError
    if not any(k in request for k in ['page_ids', 'page_titles', 'psid']):
        raise TypeError
    for non_empty_optional_list in ['page_ids', 'page_titles']:
        if non_empty_optional_list in request:
            value = request[non_empty_optional_list]
            if not value or not isinstance(value, list):
                raise TypeError
    if 'psid' in request:
        psid = request['psid']
        if not isinstance(psid, basestring) or not psid.isdigit():
            raise TypeError

def intersect_with_page_titles(cfg, page_titles):
    wiki = mwapi.MediaWikiAPI(
        'https://' + cfg.wikipedia_domain + '/w/api.php', cfg.user_agent)
    page_ids = []
    for chunk in ichunk(page_titles, PAGE_TITLES_PER_API_REQUEST):
        params = {'titles': '|'.join(chunk)}
        for response in wiki.query(params):
            if 'query' in response and 'pages' in response['query']:
                page_ids.extend(response['query']['pages'].keys())
    if not page_ids:
        return '', []
    return intersect_with_page_ids(cfg, page_ids)

def intersect_with_page_ids(cfg, page_ids):
    if not page_ids:
        return '', []
    return database.create_intersection(
        cfg.lang_code, page_ids, cfg.intersection_max_size,
        cfg.intersection_expiration_days)

def intersect_with_psid(cfg, psid):
    response = None
    try:
        with log_time('querying psid ' + psid):
            response = requests.get(
                cfg.petscan_url + '?format=json&psid=' + psid,
                timeout = cfg.petscan_timeout_s)
            articles = response.json()['*'][0]['a']['*']
            page_ids = [article['id'] for article in articles]
    except Exception as e:
        flask.current_app.logger.error(
            'PetScan request failed: ' + repr(e) + ', ' +
            repr(response.text) if response is not None else '[no response]')
        page_ids = []
    if not page_ids:
        return '', []
    return intersect_with_page_ids(cfg, page_ids)

@validate_lang_code
def create_intersection(lang_code):
    cfg = flask.g._cfg
    try:
        request = flask.request.get_json()
        validate_request_json(request)
    except:
        return flask.jsonify(error = 'Invalid request')
    if 'page_ids' in request:
        id, page_ids = intersect_with_page_ids(cfg, request['page_ids'])
    elif 'page_titles' in request:
        id, page_ids = intersect_with_page_titles(cfg, request['page_titles'])
    elif 'psid' in request:
        id, page_ids = intersect_with_psid(cfg, request['psid'])
    return flask.jsonify(
        id = id, page_ids = page_ids,
        ttl_days = cfg.intersection_expiration_days)
