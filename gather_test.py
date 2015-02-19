from __future__ import unicode_literals

from gather import extract_snippets, MARKER

import unittest
import functools

# ignore size limits to make these tests
extract_snippets = functools.partial(
    extract_snippets, minlen = 0, maxlen = float('inf'))

class ExtractSnippetTest(unittest.TestCase):
    def test_simple_Citation_needed(self):
        s = 'This needs a citation.'
        self.assertEqual(
            extract_snippets(s + '{{ Citation needed | date=July 2009 }}'),
            [s + MARKER])

    def test_simple_cn(self):
        s = 'This needs a citation.'
        self.assertEqual(
            extract_snippets(s + '{{ cn | date=July 2009 }}'),
            [s + MARKER])

    def test_split_paragraph(self):
        s = 'This is a better %s paragraph. It even countains two sentences.'
        self.assertEqual(
            extract_snippets('This is a paragraph.\n\n' + s % '{{cn}}'),
            [s % MARKER])

    def test_remove_headings(self):
        s = 'This paragraph needs a citation %s'
        self.assertEqual(
            extract_snippets('== Heading ==\n' + s % '{{cn}}'),
            [s % MARKER])

    def test_convert(self):
        s = 'The Eiffel tower is %s tall and very pretty %s.'
        self.assertEqual(
            extract_snippets(s % ('{{Convert|324|m|ft|0}}', '{{cn}}')),
            [s % ('324 m', MARKER)])

    def test_ref(self):
        s = 'The text inside references %s should go away.'
        self.assertEqual(
            extract_snippets(s % ('<ref>like this</ref>',) + '{{cn}}'),
            [s % ('',) + MARKER])

    def test_multiline_ref(self):
        s = """{{Refimprove|date=July 2009}}'''''12 Miles of Bad Road''''' is a television show originally created for [[HBO]]<ref name = "news">{{cite news
            | first =Devin
            | last =Gordon
            |author2=Johnnie L. Roberts
            | date= 2007-05-21
            | title =A Whacking Leaves HBO in Crisis
            | work =[[Newsweek]]
            | accessdate=2008-04-19
            | url =http://www.newsweek.com/id/34756
            }}</ref> centered on a Texas matriarch who must reconcile her booming real estate business and immense wealth with the day-to-day struggles of her [[dysfunctional family]] life.{{Citation needed|date=July 2009}}"""
        self.assertEqual(
            extract_snippets(s)[0],
            '12 Miles of Bad Road is a television show originally created for HBO centered on a Texas matriarch who must reconcile her booming real estate business and immense wealth with the day-to-day struggles of her dysfunctional family life.' + MARKER)

    def test_multiple_paragraphs(self):
        s = ['This needs a citation.%s', 'This also needs one%s', 'This does not.']
        self.assertEqual(
            extract_snippets('\n\n'.join(s) % ('{{cn}}', '{{cn}}')),
            [p % MARKER for p in s[:-1]])

    def test_multiple_citations_per_paragraph(self):
        s = 'This needs a citation.%s This also needs one.%s'
        self.assertEqual(
            extract_snippets(s % ('{{cn}}', '{{cn}}')),
            [s % (MARKER, MARKER)])

if __name__ == '__main__':
    unittest.main()
