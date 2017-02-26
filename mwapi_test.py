from __future__ import unicode_literals

import mwapi

import mock
import unittest

class MediaWikiAPITest(unittest.TestCase):
    TEST_API_URL = 'http://w.org/api.php'
    TEST_USER_AGENT = 'user agent'

    def setUp(self):
        self._api = mwapi.MediaWikiAPI(self.TEST_API_URL, self.TEST_USER_AGENT)

    def test_default_options(self):
        self.assertEqual(self._api.options.maxlag, 5)
        self.assertEqual(self._api.options.max_retries_maxlag, 3)

    def test_simple_query_with_options(self):
        self._api.options.maxlag = 3
        expected_request = {
            'pageids': '12345',
            'format': 'json',
            'continue': '',
            'maxlag': 3,
            'action': 'query',
            'utf8': ''
        }
        with mock.patch.object(self._api._session, 'post') as mock_post:
            mock_post.return_value = mock.MagicMock()
            mock_post.return_value.json.return_value = {}
            self.assertEquals(next(self._api.query({'pageids': '12345'})), {})
            mock_post.assert_called_once_with(
                self.TEST_API_URL, expected_request,
                headers = {'User-Agent': self.TEST_USER_AGENT})

    def test_simple_parse_with_options(self):
        self._api.options.maxlag = 3
        expected_request = {
            'text': '{{ cn }}',
            'format': 'json',
            'maxlag': 3,
            'action': 'parse',
            'utf8': ''
        }
        with mock.patch.object(self._api._session, 'post') as mock_post:
            mock_post.return_value = mock.MagicMock()
            mock_post.return_value.json.return_value = {}
            self.assertEquals(self._api.parse({'text': '{{ cn }}'}), {})
            mock_post.assert_called_once_with(
                self.TEST_API_URL, expected_request,
                headers = {'User-Agent': self.TEST_USER_AGENT})

    def test_retry_after_once(self):
        with mock.patch.object(self._api._session, 'post') as mock_post:
            with mock.patch.object(mwapi.time, 'sleep') as mock_sleep:
                mock_retry_after_response = mock.MagicMock()
                mock_retry_after_response.headers = {'Retry-After': '3.5'}
                mock_post.side_effect = [
                    mock_retry_after_response, mock.MagicMock()]
                self._api.parse({'text': 'x'})
                mock_sleep.assert_called_once_with(3.5)
                self.assertEquals(mock_post.call_count, 2)

    def test_retry_after_too_many(self):
        self._api.options.max_retries_maxlag = 1
        with mock.patch.object(self._api._session, 'post') as mock_post:
            with mock.patch.object(mwapi.time, 'sleep') as mock_sleep:
                mock_retry_after_response = mock.MagicMock()
                mock_retry_after_response.headers = {'Retry-After': '3.5'}
                mock_post.side_effect = [
                    mock_retry_after_response, mock_retry_after_response,
                    mock.MagicMock()]
                with self.assertRaises(mwapi.MediaWikiAPIError):
                    self._api.parse({'text': 'x'})
                mock_sleep.assert_called_once_with(3.5)

    def test_cache_maxlag_retry(self):
        with mock.patch.object(self._api._session, 'post') as mock_post:
            with mock.patch.object(mwapi.time, 'sleep') as mock_sleep:
                mock_maxlag_response = mock.MagicMock()
                mock_maxlag_response.json.return_value = {
                    'error': {
                        'code': 'maxlag',
                        'info': 'Waiting for host: 3.5 seconds lagged'}
                }
                mock_post.side_effect = [
                    mock_maxlag_response, mock.MagicMock()]
                self._api.parse({'text': 'x'})
                mock_sleep.assert_called_once_with(3.5)
                self.assertEquals(mock_post.call_count, 2)

    def test_no_retries_fail(self):
        self._api.options.max_retries_maxlag = 0
        with mock.patch.object(self._api._session, 'post') as mock_post:
            with mock.patch.object(mwapi.time, 'sleep') as mock_sleep:
                mock_retry_after_response = mock.MagicMock()
                mock_retry_after_response.headers = {'Retry-After': '3.5'}
                mock_post.side_effect = [
                    mock_retry_after_response, mock_retry_after_response,
                    mock.MagicMock()]
                with self.assertRaises(mwapi.MediaWikiAPIError):
                    self._api.parse({'text': 'x'})
                mock_sleep.assert_not_called()  # just raise the exception

    def test_no_retries_success(self):
        self._api.options.max_retries_maxlag = 0
        with mock.patch.object(self._api._session, 'post') as mock_post:
            with mock.patch.object(mwapi.time, 'sleep') as mock_sleep:
                mock_post.return_value = mock.MagicMock()
                self._api.parse({'text': 'x'})
                mock_sleep.assert_not_called()

if __name__ == '__main__':
    unittest.main()
