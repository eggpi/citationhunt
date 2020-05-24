from . import core

import datetime
import mock

import unittest

_CN_EXPANSION = '^[citation_needed]'
_EXPECTED_CN_HTML = (
    '<span class="{cn}">{tpl}</span>'.format(
        cn = core.CITATION_NEEDED_MARKER_CLASS, tpl = _CN_EXPANSION))

class TestConfig(object):
    lang_code = 'en'
    extract = 'snippet'
    snippet_min_size = 0
    snippet_max_size = 5000
    html_parse_parameters = {}
    citation_needed_templates = ['cn']
    html_css_selectors_to_strip = ['.noprint']

class SnippetParserTest(unittest.TestCase):
    def setUp(self):
        self._cfg = TestConfig()
        self._wp = mock.Mock()
        with mock.patch.object(
            core.SnippetParser, '_resolve_redirects_to_templates',
            side_effect = lambda x: x):
            self._sp = core.create_snippet_parser(self._wp, self._cfg)

    def _set_wikipedia_parse_response(self, html):
        self._wp.parse.return_value = {'parse': {'text': {'*': html}}}

    def _do_extract(self, html, wikitext = '{{ cn }}',
                    cn_expansion = _CN_EXPANSION):
        html = html.format(
            citation_needed_tmpl = core._CITATION_NEEDED_MARKER_MARKUP)
        # Using a single fake template id means we can only test template
        # id code paths for the first snippet in the test case :(
        html = html.format(tpl = cn_expansion,
            tpl_id = self._sp._make_template_id(0, 0))
        self._set_wikipedia_parse_response(html)
        ret = self._sp.extract(wikitext)
        call_args = None
        if self._wp.parse.call_count:
            call_args = self._wp.parse.call_args[0][0]
        return call_args, ret

    def test_simple_snippet_from_list(self):
        _, snippets = self._do_extract('''
            <p>The following is a list of elements:</p>
            <ul>
                <li>Element 1</li>
                <li>Element 2</li>
                <li>Element 3{citation_needed_tmpl}</li>
                <li>Element 4</li>
                <li>Element 5</li>
            </ul>
        ''')
        self.assertEqual(len(snippets), 1)

        # Should drop elements 1 and 5
        s = snippets[0]
        self.assertIn('<p>The following', s.snippet)
        self.assertNotIn('<li>Element 1', s.snippet)
        self.assertIn('<li>Element 2', s.snippet)
        self.assertIn('<li>Element 3', s.snippet)
        self.assertIn(core.CITATION_NEEDED_MARKER_CLASS, s.snippet)
        self.assertIn('<li>Element 4', s.snippet)
        self.assertNotIn('<li>Element 5', s.snippet)

    def test_multiple_snippets_from_list(self):
        _, snippets = self._do_extract('''
            <p>The following is a list of elements:</p>
            <ul>
                <li>Element 1</li>
                <li>Element 2</li>
                <li>Element 3{citation_needed_tmpl}</li>
                <li>Element 4</li>
                <li>Element 5{citation_needed_tmpl}</li>
            </ul>
        ''')
        snippets = sorted(s.snippet for s in snippets)
        self.assertEqual(len(snippets), 2)

        self.assertIn('<p>The following', snippets[0])
        self.assertIn('<li>Element 3' + _EXPECTED_CN_HTML + '</li>', snippets[0])
        self.assertNotIn('<li>Element 5' + _EXPECTED_CN_HTML + '</li>', snippets[0])

        self.assertIn('<p>The following', snippets[1])
        self.assertIn('<li>Element 5' + _EXPECTED_CN_HTML + '</li>', snippets[1])
        self.assertNotIn('<li>Element 3' + _EXPECTED_CN_HTML + '</li>', snippets[1])

    def test_no_nested_lists(self):
        _, snippets = self._do_extract('''
            <p>The following is a list of elements:</p>
            <ul>
                <li>Element 1</li>
                <li>Element 2</li>
                <li>Element 3{citation_needed_tmpl}</li>
                <li>Element 4
                  <ol><li>Element 4.1</li></ol>
                </li>
                <li>Element 5</li>
            </ul>
        ''')
        self.assertEqual(len(snippets), 1)
        self.assertIn('<li>Element 2', snippets[0].snippet)
        self.assertIn('<li>Element 3', snippets[0].snippet)
        self.assertIn(core.CITATION_NEEDED_MARKER_CLASS, snippets[0].snippet)
        # Should not include Element 4 or Element 4.1
        self.assertNotIn('<li>Element 4', snippets[0].snippet)

    def test_remove_space_before_marker(self):
        _, snippets = self._do_extract('''
            <p>This is some HTML  {citation_needed_tmpl} with space.</p>''')
        expected = '<div class="%s"><p>This is some HTML' % (
            core.SNIPPET_WRAPPER_CLASS) + _EXPECTED_CN_HTML + ' with space.</p></div>'
        self.assertEqual(snippets[0].snippet, expected)

    def test_drop_ref_groups(self):
        wikitext, _ = self._do_extract('html', '{{ cn }}<ref group="g"/>')
        self.assertNotIn('group', wikitext)

    def test_strip_css_selectors(self):
        _, snippets = self._do_extract(
            '<p><span class="noprint">Non-important</span> '
            'Stuff {citation_needed_tmpl}</p>',
            '{{ cn }}', '<span class="noprint">Important stuff!</span>')

        self.assertNotIn('Non-important', snippets[0].snippet)
        self.assertIn('Important stuff!', snippets[0].snippet)

    def test_strip_attributes(self):
        _, snippets = self._do_extract(
            '<p><span class="theclass">Stuff</span>{citation_needed_tmpl}</p>')
        self.assertNotIn('theclass', snippets[0].snippet)

    def test_extract_section(self):
        self._cfg.extract = 'section'
        _, snippets = self._do_extract(
            '<p>{citation_needed_tmpl}<p><p>Full</p><p>Section</p>',
            '{{cn}}\n\nFull\n\nSection')
        expected = '<div class="%s"><p>Full</p><p>Section</p></div>' % (
            core.SNIPPET_WRAPPER_CLASS)
        self.assertEqual(expected, snippets[0].snippet)

    def test_no_wikicode_in_section_titles(self):
        _, snippets = self._do_extract(
            '<p>Irrelevant HTML content{citation_needed_tmpl}</p>',
            "== Section title ''with Wikicode'' == \n\nIrrelevant content{{cn}}")
        self.assertEqual(snippets[0].section, 'Section title with Wikicode')

    def test_multiple_snippets_in_section(self):
        _, snippets = self._do_extract(
            '<p>This needs a reference{citation_needed_tmpl}</p>'
            '<p>So does this{citation_needed_tmpl}</p>'
            '''<p>The following is a list of elements:</p>
            <ul>
                <li>Element 1</li>
                <li>Element 2{citation_needed_tmpl}</li>
                <li>Element 3</li>
            </ul>''')
        snippets = sorted(s.snippet for s in snippets)
        self.assertEqual(3, len(snippets))
        self.assertEqual(
            '<div class="%s"><p>So does this%s</p></div>' % (
                core.SNIPPET_WRAPPER_CLASS, _EXPECTED_CN_HTML), snippets[0])
        self.assertIn('Element 2%s' % _EXPECTED_CN_HTML, snippets[1])
        self.assertEqual(
            '<div class="%s"><p>This needs a reference%s</p></div>' % (
                core.SNIPPET_WRAPPER_CLASS, _EXPECTED_CN_HTML), snippets[2])

    def test_no_duplicate_snippet(self):
        _, snippets = self._do_extract(
            ('<p>This{citation_needed_tmpl} needs a '
                'reference{citation_needed_tmpl}</p>'),
            'This{{cn}} needs a reference{{cn}}')
        snippets = [s.snippet for s in snippets]
        self.assertEqual([
            '<div class="%s"><p>This%s needs a reference%s</p></div>' % (
                core.SNIPPET_WRAPPER_CLASS, _EXPECTED_CN_HTML, _EXPECTED_CN_HTML),
            ], snippets)

    def test_extract_date_enwiki(self):
        _, snippets = self._do_extract(
            '<p>Simple{citation_needed_tmpl} test.</p>',
            'This{{cn|date=January 2020}} needs a reference{{cn}}')
        self.assertEqual(snippets[0].dates[0], datetime.datetime(
            year = 2020, month = 1, day = 1))

    def test_ignore_bad_date_enwiki(self):
        _, snippets = self._do_extract(
            '<p>Simple{citation_needed_tmpl} test.</p>',
            'This{{cn|date=January 3, 2020}} needs a reference{{cn}}')
        self.assertEqual(snippets[0].dates, [])

    def test_ignore_date_other_wikis(self):
        self._cfg.lang_code = 'es'
        _, snippets = self._do_extract(
            '<p>Simple{citation_needed_tmpl} test.</p>',
            'This{{cn|date=January 2020}} needs a reference{{cn}}')
        self.assertEqual(snippets[0].dates, [])

if __name__ == '__main__':
    unittest.main()
