from . import database
from utils import *
from .common import *

@validate_lang_code
def snippets_in_articles(lang_code):
    cfg = flask.g._cfg
    try:
        page_ids = flask.request.args.getlist('page_id', type=int)
    except ValueError:
        return flask.jsonify(error = 'Invalid request')
    if not page_ids:
        return flask.jsonify(error = 'Invalid request')
    result = database.get_snippets_in_articles(
        lang_code, page_ids, cfg.api.max_returned_snippets)
    return flask.jsonify({
        page_id: [
            flask.url_for('citation_hunt',
                id = snippet_id, lang_code = lang_code, _external = True)
            for snippet_id in snippet_ids
        ]
    for page_id, snippet_ids in result.items()})
