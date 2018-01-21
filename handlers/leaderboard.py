import database
from utils import *
from common import *

import flask

import collections

LeaderboardEntry = collections.namedtuple(
    'LeaderboardEntry', ['user', 'count'])

@validate_lang_code
def leaderboard(lang_code):
    ndays = 30
    rev_ids = database.query_fixed_revisions(lang_code, ndays)
    leaderboard = []
    if rev_ids:
        users = database.query_rev_users(lang_code, rev_ids)
        leaderboard = [
            LeaderboardEntry(*e) for e in
            collections.Counter(users).most_common(50)]
    return flask.render_template(
        'leaderboard.html',
        leaderboard = leaderboard,
        ndays = ndays,
        strings = flask.g._strings,
        config = flask.g._cfg,
        lang_tag = flask.g._lang_tag,
        lang_code = lang_code)
