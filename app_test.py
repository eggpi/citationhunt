import os
os.environ['DEBUG'] = '1' # disable https redirects

# Disable stats since it requires a database, and we're not
# testing it anyway
import config
config.get_global_config().flagged_off.append('stats')

import app
import mock

import time
import datetime
import unittest

class CitationHuntTest(unittest.TestCase):
    def setUp(self):
        self.app = app.app.test_client()

        self.sid = '93b6f3cf'
        self.cat = 'b5e1a25d'
        self.fake_snippet_info = (
            'Some snippet', 'Some section',
            'https://en.wikipedia.org/wiki/A', 'Some title')

        methods_and_return_values = [
            ('query_snippet_by_category', (self.sid,)),
            ('query_random_snippet', (self.sid,)),
            ('query_next_id', (self.sid[::-1],)),
            ('query_fixed_snippets', 6)
        ]

        self.patchers = [
            mock.patch('app.handlers.Database.' + m, return_value = rv)
            for m, rv in methods_and_return_values
        ]
        self.patchers.append(
            mock.patch('app.handlers.Database.query_category_by_id', wraps = (
                lambda _, id: (self.cat, 'C') if id == self.cat else None)))
        self.patchers.append(
            mock.patch('app.handlers.Database.query_snippet_by_id',wraps = (
                lambda _, id: self.fake_snippet_info if id == self.sid else None)
        ))
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def get_url_args(self, url):
        return dict(kv.split('=') for kv in url[url.rfind('?')+1:].split('&'))

    def test_default_en_redirect_no_accept_language(self):
        with mock.patch.dict(
            config.LANG_CODES_TO_ACCEPT_LANGUAGE, {
                'en': [], 'ru': []
            }, True):
            response = self.app.get('/')
            self.assertEquals(response.status_code, 302)
            self.assertTrue(response.location.endswith('/en'))

            # Must preserve path
            response = self.app.get('/favicon.ico')
            self.assertEquals(response.status_code, 302)
            self.assertTrue(response.location.endswith('/en/favicon.ico'))

    def test_accept_language_redirect(self):
        headers = {'Accept-Language': 'ru'}
        with mock.patch.dict(
            config.LANG_CODES_TO_LANG_NAMES, {
                'en': '', 'ru': ''
            }, True):
            response = self.app.get('/', headers = headers)
            self.assertEquals(response.status_code, 302)
            self.assertTrue(response.location.endswith('/ru'))

            # We don't really bother telling apart a path and an invalid lang
            # code, so this just redirects to /en, not /ru
            response = self.app.get('/favicon.ico', headers = headers)
            self.assertEquals(response.status_code, 302)
            self.assertTrue(response.location.endswith('/en/favicon.ico'))

    def test_default_en_redirect_unsupported_language(self):
        headers = {'Accept-Language': 'lv'}
        # Pretend we don't support lv
        with mock.patch.dict(config.LANG_CODES_TO_ACCEPT_LANGUAGE,
                {'en': ''}, True):
            response = self.app.get('/', headers = headers)
        self.assertEquals(response.status_code, 302)
        self.assertTrue(response.location.endswith('/en'))

    def test_no_id_no_category(self):
        response = self.app.get('/en')
        args = self.get_url_args(response.location)

        self.assertEquals(response.status_code, 302)
        self.assertEquals(args['id'], self.sid)
        self.assertEquals(args['cat'], app.handlers.CATEGORY_ALL.id)

    def test_id_no_category(self):
        response = self.app.get('/en?id=' + self.sid)
        self.assertEquals(response.status_code, 200)

    def test_invalid_id_no_category(self):
        response = self.app.get('/en?id=invalid')
        self.assertEquals(response.status_code, 404)

    def test_invalid_id_valid_category(self):
        response = self.app.get('/en?id=invalid&cat=' + self.cat)
        self.assertEquals(response.status_code, 404)

    def test_id_valid_category(self):
        response = self.app.get('/en?id=' + self.sid + '&cat=' + self.cat)
        self.assertEquals(response.status_code, 200)

    def test_no_id_invalid_category(self):
        response = self.app.get('/en?cat=invalid')
        args = self.get_url_args(response.location)

        self.assertEquals(response.status_code, 302)
        self.assertTrue('id' not in args)
        self.assertEquals(args['cat'], app.handlers.CATEGORY_ALL.id)

    def test_no_id_valid_category(self):
        response = self.app.get('/en?cat=' + self.cat)
        args = self.get_url_args(response.location)

        self.assertEquals(response.status_code, 302)
        self.assertEquals(args['id'], self.sid)
        self.assertEquals(args['cat'], self.cat)

        # Now request the snippet, should be a 200
        response = self.app.get(
            '/en?id=%s&cat=%s' % (args['id'], args['cat']))
        self.assertEquals(response.status_code, 200)

    def test_id_invalid_category(self):
        response = self.app.get('/en?id=' + self.sid + '&cat=invalid')
        args = self.get_url_args(response.location)

        self.assertEquals(response.status_code, 302)
        self.assertEquals(args['id'], self.sid)
        self.assertEquals(args['cat'], app.handlers.CATEGORY_ALL.id)

    def test_cache_control(self):
        response = self.app.get('/en?id=%s&cat=all' % self.sid)
        self.assertEquals(response.status_code, 200)
        self.assertTrue('public' in response.cache_control)
        self.assertEquals(
            response.cache_control.max_age, app.CACHE_DURATION_SNIPPET)

        response = self.app.get('/')
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response.cache_control.max_age, None)

    def test_redirect(self):
        response = self.app.get('/en/redirect?to=wiki/AT%26T#History')
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response.headers['Location'],
            'https://en.wikipedia.org/wiki/AT&T#History')

    def test_fixed_small_time_window(self):
        now = time.time()
        from_ts = int(now - 6 * 3600)
        response = self.app.get('/en/fixed?from_ts=' + str(from_ts))

        # only 6 hours ago, pass the date through
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.get_data(), '6')
        app.handlers.Database.query_fixed_snippets.assert_called_once_with(
            'en', datetime.datetime.fromtimestamp(from_ts))

    def test_fixed_garbage_ts(self):
        response = self.app.get('/en/fixed?from_ts=garbage')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.get_data(), '6')

        now = datetime.datetime.today()
        normalized = app.handlers.Database.query_fixed_snippets.call_args[0][1]
        self.assertTrue((now - normalized) > datetime.timedelta(hours = 23))
        self.assertTrue((now - normalized) < datetime.timedelta(hours = 25))

    def test_fixed_ts_not_provided(self):
        response = self.app.get('/en/fixed')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.get_data(), '6')

        now = datetime.datetime.today()
        normalized = app.handlers.Database.query_fixed_snippets.call_args[0][1]
        self.assertTrue((now - normalized) > datetime.timedelta(hours = 23))
        self.assertTrue((now - normalized) < datetime.timedelta(hours = 25))

    def test_fixed_ts_too_old(self):
        now = time.time()
        from_ts = int(now - 48 * 3600)
        now = datetime.datetime.fromtimestamp(now)
        response = self.app.get('/en/fixed?from_ts=' + str(from_ts))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.get_data(), '6')

        normalized = app.handlers.Database.query_fixed_snippets.call_args[0][1]
        self.assertTrue((now - normalized) > datetime.timedelta(hours = 23))
        self.assertTrue((now - normalized) < datetime.timedelta(hours = 25))

if __name__ == '__main__':
    unittest.main()
