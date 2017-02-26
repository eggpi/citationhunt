import requests

import logging
import re
import time

# https://www.mediawiki.org/wiki/Manual:Maxlag_parameter
_MAXLAG_ERROR_REGEX = re.compile(
    r'Waiting for [^ ]*: ([0-9.-]+) seconds lagged')

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())

class MediaWikiAPIError(Exception):
    def __init__(self, message, response):
        super(MediaWikiAPIError, self).__init__(message)
        self.response = response

class MediaWikiAPIOptions(object):
    def __init__(self):
        self._options = {}
        self._params = {'format': 'json', 'utf8': ''}

        self._dict_key_to_property(
            self._options, 'max_retries_maxlag',
            'max retries for API requests that hit maxlag limits')
        self.max_retries_maxlag = 3

        self._dict_key_to_property(
            self._params, 'maxlag', 'maxlag for API requests (seconds)')
        self.maxlag = 5

    def _dict_key_to_property(self, dict, key, doc):
        def g(self):
            return dict[key]
        def s(self, value):
            dict[key] = value
        # http://stackoverflow.com/a/1355444
        setattr(type(self), key, property(g, s, None, doc))

    def build_params(self, params):
        return dict(self._params, **params)

class MediaWikiAPI(object):
    def __init__(self, url, user_agent):
        self._url = url
        self._session = requests.Session()
        self._headers = {
            'User-Agent': user_agent,
        }
        self.options = MediaWikiAPIOptions()

    def _do_request(self, params):
        response = None
        retries = self.options.max_retries_maxlag
        for r in range(retries + 1):
            res = self._session.post(self._url, params, headers = self._headers)
            if 'Retry-After' in res.headers:
                if r < retries:
                    sleep_s = float(res.headers['Retry-After'])
                    _logger.warning(
                        'got Retry-After header, sleeping for %.2f seconds',
                        sleep_s)
                    time.sleep(sleep_s)
                continue
            response = res.json()
            if 'error' in response:
                if response['error']['code'] == 'maxlag':
                    match = _MAXLAG_ERROR_REGEX.search(
                        response['error']['info'])
                    if match:
                        if r < retries:
                            sleep_s = float(match.group(1))
                            _logger.warning(
                                'got maxlag error, sleeping for %.2f seconds',
                                sleep_s)
                            time.sleep(sleep_s)
                        continue
                else:
                    raise MediaWikiAPIError(
                        response['error'].get('info', ''), response)
            return response
        raise MediaWikiAPIError('Exhausted maxlag retries!', response)

    def query(self, params):
        params = self.options.build_params(params)
        params['action'] = 'query'
        params['continue'] = ''
        while True:
            response = self._do_request(params)
            yield response
            if 'continue' not in response:
                break
            params.update(response['continue'])

    def parse(self, params):
        params = self.options.build_params(params)
        params['action'] = 'parse'
        return self._do_request(params)

    # Utility methods, also serve as examples
    def get_page_contents(self, title = None, pageid = None):
        params = {
            'prop': 'revisions',
            'rvprop': 'content'
        }
        if title is not None:
            params['titles'] = title
        elif pageid is not None:
            params['pageids'] = pageid
        else:
            raise MediaWikiAPIError('Either title or pageid must be present')
        contents = ''
        for response in self.query(params):
            for page in response['query']['pages'].values():
                contents += page['revisions'][0]['*']
        return contents

if __name__ == '__main__':
    import pprint
    api = MediaWikiAPI(
        'https://en.wikipedia.org/w/api.php',
        'citationhunt (https://tools.wmflabs.org/citationhunt)')
    api.options.maxlag = 10
    print api.parse({'text': '{{ cn }}', 'contentmodel': 'wikitext'})
