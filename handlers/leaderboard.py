import chdb
from utils import *
from common import *

import flask

import collections

LeaderboardEntry = collections.namedtuple(
    'LeaderboardEntry', ['user', 'count'])

@validate_lang_code
def leaderboard(lang_code):
    wpdb = chdb.init_wp_replica_db(lang_code)
    statsdb = chdb.init_stats_db()

    rev_ids = [
        str(row[0]) for row in statsdb.execute_with_retry_s(
        '''SELECT rev_id FROM fixed_''' + lang_code +
        ''' WHERE DATEDIFF(NOW(), clicked_ts) < 30''')]
    leaderboard = []
    if rev_ids:
        users = [
            row[0] for row in wpdb.execute_with_retry_s('''
            SELECT rev_user_text FROM revision_userindex
            WHERE rev_id IN (%s)''' % ','.join(rev_ids))]
        leaderboard = [
            LeaderboardEntry(*e) for e in
            collections.Counter(users).most_common(50)]
    return flask.render_template(
        'leaderboard.html',
        leaderboard = leaderboard,
        strings = flask.g._strings,
        config = flask.g._cfg,
        lang_tag = flask.g._lang_tag,
        lang_code = lang_code)
