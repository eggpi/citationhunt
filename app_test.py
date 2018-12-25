#-*- encoding: utf-8 -*-
from __future__ import unicode_literals

import os
os.environ['DEBUG'] = '1' # disable https redirects

# Disable stats since it requires a database, and we're not
# testing it anyway
import config
config.get_global_config().flagged_off.append('stats')

import app
import mock

import requests

import time
import datetime
import json
import unittest

class CitationHuntTest(unittest.TestCase):
    def setUp(self):
        self.app = app.app.test_client()

        self.sid = '93b6f3cf'
        self.cat = 'b5e1a25d'
        self.inter = 'c4a1e27d'
        self.fake_snippet_info = (
            'Some snippet', 'Some section',
            'https://en.wikipedia.org/wiki/A', 'Some title')

        methods_and_return_values = [
            ('query_snippet_by_category', (self.sid,)),
            ('query_snippet_by_intersection', (self.sid,)),
            ('query_random_snippet', (self.sid,)),
            ('query_next_id_in_category', (self.sid[::-1],)),
            ('query_next_id_in_intersection', (self.sid[::-1],)),
            ('query_fixed_snippets', 6)
        ]

        self.patchers = [
            mock.patch('app.handlers.database.' + m, return_value = rv)
            for m, rv in methods_and_return_values
        ]
        self.patchers.append(
            mock.patch('app.handlers.database.query_category_by_id', wraps = (
                lambda _, id: (self.cat, 'C') if id == self.cat else None)))
        self.patchers.append(
            mock.patch('app.handlers.database.query_snippet_by_id',wraps = (
                lambda _, id: self.fake_snippet_info if id == self.sid else None)
        ))
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def get_url_args(self, url):
        if '?' not in url:
            return {}
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

    def test_trailing_slash(self):
        response = self.app.get('/en/')
        self.assertEquals(response.status_code, 302)
        self.assertTrue('/en?' in response.location)

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

    def test_zh_redirects(self):
        # Just use the real config for these, make sure we properly
        # match Chinese headers with the lang code
        response = self.app.get('/', headers = {'Accept-Language': 'zh-TW'})
        self.assertEquals(response.status_code, 302)
        self.assertTrue(response.location.endswith('/zh_hant'))

        response = self.app.get('/', headers = {'Accept-Language': 'zh-CN'})
        self.assertEquals(response.status_code, 302)
        self.assertTrue(response.location.endswith('/zh_hans'))

    def test_zh_html_lang(self):
        # Again using the new config, request zh_hans and make sure the
        # language attribute is set correctly in the response
        response = self.app.get('/zh_hans?id=' + self.sid)
        self.assertIn('lang="zh-Hans"', response.data.decode('utf-8'))

    def test_kea_redirect(self):
        # Accept-Language: kea should redirect to pt with no snippet.
        response = self.app.get('/', headers = {'Accept-Language': 'kea,pt'})
        self.assertEquals(response.status_code, 302)
        self.assertTrue(response.location.endswith('/pt'))

        # Also with snippet, but the UI should show kea strings.
        response = self.app.get('/pt?id=' + self.sid,
            headers = {'Accept-Language': 'kea,pt'})
        self.assertIn('lang="kea"', response.data.decode('utf-8'))

    def test_pt_fallback(self):
        # Fallback to pt-BR for ptwiki if no matching Accept-Language header
        # is used.
        response = self.app.get('/pt?id=' + self.sid,
            headers = {'Accept-Language': 'en'})
        self.assertIn('lang="pt-BR"', response.data.decode('utf-8'))

    def test_no_id_no_category(self):
        response = self.app.get('/en')
        args = self.get_url_args(response.location)

        self.assertEquals(response.status_code, 302)
        self.assertEquals(args['id'], self.sid)
        self.assertNotIn('cat', args)

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
        self.assertEquals(args, {})

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

    def test_no_id_empty_category(self):
        response = self.app.get('/en?cat=')
        args = self.get_url_args(response.location)

        self.assertEquals(response.status_code, 302)
        self.assertEquals(args['id'], self.sid)
        self.assertNotIn('cat', args)

    def test_id_invalid_category(self):
        response = self.app.get('/en?id=' + self.sid + '&cat=invalid')
        args = self.get_url_args(response.location)

        # Strip the invalid category
        self.assertEquals(response.status_code, 302)
        self.assertEquals(args['id'], self.sid)
        self.assertNotIn('cat', args)

    def test_no_id_valid_intersection(self):
        response = self.app.get('/en?custom=' + self.inter)
        args = self.get_url_args(response.location)

        self.assertEquals(response.status_code, 302)
        self.assertEquals(args['id'], self.sid)
        self.assertEquals(args['custom'], self.inter)

        # Now request the snippet, should be a 200
        response = self.app.get(
            '/en?id=%s&custom=%s' % (args['id'], args['custom']))
        self.assertEquals(response.status_code, 200)

    # Shouldn't really happen, just make sure we don't crash or anything.
    def test_category_and_intersection(self):
        response = self.app.get('/en?custom=' + self.inter + '&cat=' + self.cat)
        args = self.get_url_args(response.location)

        self.assertEquals(response.status_code, 302)
        self.assertEquals(args['id'], self.sid)
        self.assertEquals(args['cat'], self.cat)
        self.assertNotIn('custom', args)

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
        app.handlers.database.query_fixed_snippets.assert_called_once_with(
            'en', datetime.datetime.fromtimestamp(from_ts))

    def test_fixed_garbage_ts(self):
        response = self.app.get('/en/fixed?from_ts=garbage')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.get_data(), '6')

        now = datetime.datetime.today()
        normalized = app.handlers.database.query_fixed_snippets.call_args[0][1]
        self.assertTrue((now - normalized) > datetime.timedelta(hours = 23))
        self.assertTrue((now - normalized) < datetime.timedelta(hours = 25))

    def test_fixed_ts_not_provided(self):
        response = self.app.get('/en/fixed')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.get_data(), '6')

        now = datetime.datetime.today()
        normalized = app.handlers.database.query_fixed_snippets.call_args[0][1]
        self.assertTrue((now - normalized) > datetime.timedelta(hours = 23))
        self.assertTrue((now - normalized) < datetime.timedelta(hours = 25))

    def test_fixed_ts_too_old(self):
        now = time.time()
        from_ts = int(now - 48 * 3600)
        now = datetime.datetime.fromtimestamp(now)
        response = self.app.get('/en/fixed?from_ts=' + str(from_ts))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.get_data(), '6')

        normalized = app.handlers.database.query_fixed_snippets.call_args[0][1]
        self.assertTrue((now - normalized) > datetime.timedelta(hours = 23))
        self.assertTrue((now - normalized) < datetime.timedelta(hours = 25))

    @mock.patch('app.handlers.database.query_fixed_revisions',
        return_value = [])
    def test_leaderboard_empty(self, _):
        response = self.app.get('/en/leaderboard.html')
        self.assertEquals(response.status_code, 200)

    @mock.patch('app.handlers.database.query_fixed_revisions',
        return_value = range(10))
    @mock.patch('app.handlers.database.query_rev_users',
        return_value = ['Aliçe'] * 4 + ['Bob'] * 6)
    def test_leaderboard(self, *mocks):
        response = self.app.get('/en/leaderboard.html').get_data().decode(
            'utf-8')
        self.assertIn('Aliçe', response)
        self.assertIn('4', response)
        self.assertIn('Bob', response)
        self.assertIn('6', response)

    def test_broken_intersection_input(self):
        broken_inputs = [
            '',
            {'page_ids': ''},
            {'page_titles': ''},
            {'petscan_id': ''},
            {'page_ids': []},
            {'page_titles': []},
            {'psid': []},
            {'psid': 'invalid'},
        ]
        for bi in broken_inputs:
            response = json.loads(
                self.app.post('/en/intersection',
                    data = json.dumps(bi),
                    headers = {'Content-Type': 'application/json'}).data)
            self.assertEquals(response, {'error': 'Invalid request'})

    @mock.patch('app.handlers.intersections.requests.get')
    @mock.patch('app.handlers.database.create_intersection')
    def test_petscan_ok(self, mock_create_intersection, mock_get):
        mock_response = mock_get()
        mock_response.json.return_value = {
            '*': [{'a': {'*': [{'id': i} for i in range(10)]}}]}
        mock_create_intersection.return_value = (self.inter, range(5))
        response = json.loads(
            self.app.post('/en/intersection',
                data = json.dumps({'psid': '123456'}),
                headers = {'Content-Type': 'application/json'}).data)
        self.assertEquals(response['id'], self.inter)
        self.assertEquals(response['page_ids'], range(5))
        self.assertEquals(response['ttl_days'],
            config.get_global_config().intersection_expiration_days)

    @mock.patch('app.handlers.intersections.requests.get')
    def test_petscan_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout
        response = json.loads(
            self.app.post('/en/intersection',
                data = json.dumps({'psid': '123456'}),
                headers = {'Content-Type': 'application/json'}).data)
        self.assertEquals(response['id'], '')
        self.assertEquals(response['page_ids'], [])
        self.assertEquals(response['ttl_days'],
            config.get_global_config().intersection_expiration_days)

    @mock.patch('app.handlers.intersections.requests.get')
    def test_petscan_no_articles(self, mock_get):
        mock_response = mock_get()
        mock_response.json.return_value = {'*': [{'a': {'*': []}}]}
        response = json.loads(
            self.app.post('/en/intersection',
                data = json.dumps({'psid': '123456'}),
                headers = {'Content-Type': 'application/json'}).data)
        self.assertEquals(response['id'], '')
        self.assertEquals(response['page_ids'], [])
        self.assertEquals(response['ttl_days'],
            config.get_global_config().intersection_expiration_days)

    @mock.patch('app.handlers.intersections.requests.get')
    @mock.patch('app.handlers.database.create_intersection')
    def test_petscan_no_known_articles(
        self, mock_create_intersection, mock_get):
        mock_response = mock_get()
        mock_response.json.return_value = {
            '*': [{'a': {'*': [{'id': i} for i in range(10)]}}]}
        mock_create_intersection.return_value = ('', [])
        response = json.loads(
            self.app.post('/en/intersection',
                data = json.dumps({'psid': '123456'}),
                headers = {'Content-Type': 'application/json'}).data)
        self.assertEquals(response['id'], '')
        self.assertEquals(response['page_ids'], [])
        self.assertEquals(response['ttl_days'],
            config.get_global_config().intersection_expiration_days)

if __name__ == '__main__':
    unittest.main()
