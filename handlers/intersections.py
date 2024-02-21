import chdb
import config
from . import database
from utils import *
from .common import *

import requests

# https://www.mediawiki.org/wiki/API:Query#Specifying_pages
PAGE_TITLES_PER_API_REQUEST = 50

# do a little basic type checking
def validate_request_json(request):
    if not isinstance(request, dict):
        raise TypeError
    if not any(k in request for k in ['page_ids', 'page_titles', 'psid', 'pileid']):
        raise TypeError
    for non_empty_optional_list in ['page_ids', 'page_titles']:
        if non_empty_optional_list in request:
            value = request[non_empty_optional_list]
            if not value or not isinstance(value, list):
                raise TypeError
    if 'psid' in request:
        psid = request['psid']
        if not isinstance(psid, str) or not psid.isdigit():
            raise TypeError
    if 'pileid' in request:
        pileid = request['pileid']
        if not isinstance(pileid, str) or not pileid.isdigit():
            raise TypeError

def intersect_with_page_titles(cfg, page_titles):
    cfg.enable_wikipedia_api()
    page_ids = []
    for chunk in ichunk(page_titles, PAGE_TITLES_PER_API_REQUEST):
        params = {'titles': '|'.join(chunk)}
        for response in cfg.wikipedia.query(params):
            if 'query' in response and 'pages' in response['query']:
                page_ids.extend(list(response['query']['pages'].keys()))
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
        wiki_name = cfg.database.rstrip('_p')
        with log_time('querying psid ' + psid):
            response = requests.get(
                cfg.petscan_url + '?format=json&psid=' + psid +
                    # Try to fetch enough results that, when intersected with
                    # our database, we get cfg.intersection_max_size pages.
                    '&output_limit=' + str(cfg.intersection_max_size * 2) +
                    # Ask PetScan to give us results in the Wiki we're serving
                    # from, even if the original query refers to different Wiki.
                    '&common_wiki=other&common_wiki_other=' + wiki_name,
                timeout = cfg.petscan_timeout_s)
            articles = response.json()['*'][0]['a']['*']
            page_ids = [article['id'] for article in articles]
    except Exception as e:
        flask.current_app.logger.warning(
            'PetScan request failed: ' + repr(e) + ', ' +
            (repr(response.text) if response is not None else '[no response]'))
        page_ids = []
    if not page_ids:
        return '', []
    return intersect_with_page_ids(cfg, page_ids)

def intersect_with_pileid(cfg, pileid):
    page_titles = []
    response = None
    try:
        response = requests.get(
            cfg.pagepile_url + '/api.php?id=' + pileid +
            '&action=get_data&format=json',
            timeout = cfg.pagepile_timeout_s)
        response_json = response.json()
        wiki = response_json['wiki']
        if wiki == cfg.database.rstrip('_p'):
            page_titles = response_json['pages']
    except Exception as e:
        flask.current_app.logger.warning(
            'Pagepile request failed: ' + repr(e) + ', ' +
            (repr(response.text) if response is not None else '[no response]'))
    if not page_titles:
        return '', []
    return intersect_with_page_titles(cfg, page_titles)

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
    elif 'pileid' in request:
        id, page_ids = intersect_with_pileid(cfg, request['pileid'])
    return flask.jsonify(
        id = id, page_ids = page_ids,
        ttl_days = cfg.intersection_expiration_days)
