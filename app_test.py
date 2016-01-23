import os
os.environ['DEBUG'] = '1' # disable https redirects

import app
import chdb

import unittest

class CitationHuntTest(unittest.TestCase):
    def setUp(self):
        self.app = app.app.test_client()
        db = chdb.init_db('en')
        cursor = db.cursor()

        # FIXME should really mock chdb instead.
        cursor.execute('SELECT snippets.id, category_id FROM ' \
            'snippets, articles_categories WHERE ' \
            'snippets.article_id = articles_categories.article_id ' \
            'LIMIT 1;')
        self.sid, self.cat = cursor.fetchone()

    def get_url_args(self, url):
        return dict(kv.split('=') for kv in url[url.rfind('?')+1:].split('&'))

    def test_default_en_redirect(self):
        response = self.app.get('/')
        self.assertEquals(response.status_code, 302)
        self.assertTrue(response.location.endswith('/en'))

    def test_no_id_no_category(self):
        response = self.app.get('/en')
        args = self.get_url_args(response.location)

        self.assertEquals(response.status_code, 302)
        self.assertTrue('id' in args)
        self.assertEquals(args['cat'], app.CATEGORY_ALL.id)

    def test_id_no_category(self):
        response = self.app.get('/en?id=' + self.sid)
        self.assertEquals(response.status_code, 200)

    def test_id_valid_category(self):
        response = self.app.get('/en?id=' + self.sid + '&cat=' + self.cat)
        self.assertEquals(response.status_code, 200)

    def test_no_id_invalid_category(self):
        response = self.app.get('/en?cat=invalid')
        args = self.get_url_args(response.location)

        self.assertEquals(response.status_code, 302)
        self.assertTrue('id' not in args)
        self.assertEquals(args['cat'], app.CATEGORY_ALL.id)

    def test_no_id_valid_category(self):
        response = self.app.get('/en?cat=' + self.cat)
        args = self.get_url_args(response.location)

        self.assertEquals(response.status_code, 302)
        self.assertTrue('id' in args)
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
        self.assertEquals(args['cat'], app.CATEGORY_ALL.id)

    def test_cache_control(self):
        response = self.app.get('/en/categories.html')
        self.assertTrue('public' in response.cache_control)
        self.assertTrue('max-age' in response.cache_control)

    def test_gzip(self):
        with app.app.test_request_context('/en/categories.html'):
            response = self.app.get('/en/categories.html',
                headers = {'Accept-encoding': 'gzip'})
            response = app.app.process_response(response)

            self.assertEquals(response.content_encoding, 'gzip')

if __name__ == '__main__':
    unittest.main()
