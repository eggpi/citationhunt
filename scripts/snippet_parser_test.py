from __future__ import unicode_literals

from snippet_parser import extract_snippets, MARKER

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

    def test_citation_inside_template_false_positive(self):
        s = '''{{Two other uses||the Irish football player|Anton Rodgers (footballer)|those of a similar name|Anthony Rogers (disambiguation)}}
            <!--Anthony Rodgers redirects here-->
            {{Infobox person
            | name        = Anton Rodgers
            | image       = Anton Rodgers.jpg
            | imagesize   =
            | caption     =
            | birth_name  = Anthony Rodgers
            | birth_date  = {{Birth date|1933|1|10|df=y}}<ref>http://www.imdb.com/name/nm0734668/</ref>
            | birth_place = [[London]], UK
            | death_date  = {{death date and age|2007|12|1|1933|1|10|df=y}}<ref>http://www.imdb.com/name/nm0734668/</ref>
            | death_place = [[Reading, Berkshire]], UK
            | occupation  = [[Actor]]
            | spouse      = Morna Eugenie Watson<!-- marriage span? --><ref name=filmr/><br>[[Elizabeth Garvie]] (1983{{citation needed|date=April 2011}}&ndash;2007)
            }}
            \'\'\'Anton Rodgers\'\'\' (born \'\'\'Anthony Rodgers\'\'\';<ref>http://ftvdb.bfi.org.uk/sift/individual/16060</ref> 10 January 1933 &ndash; 1 December 2007) was an [[English people|English]] actor and occasional director. He performed on stage, in film, in television dramas and [[Situation comedy|sitcoms]] and in animation.<ref>{{cite news |title= Anton Rodgers |work=telegraph.co.uk |url=http://www.telegraph.co.uk/news/main.jhtml?view=DETAILS&grid=&xml=/news/2007/12/03/db0301a.xml |date=2007-12-03 |accessdate=2007-12-03| archiveurl= http://web.archive.org/web/20071203205358/http://www.telegraph.co.uk/news/main.jhtml?view=DETAILS&grid=&xml=/news/2007/12/03/db0301a.xml| archivedate= 3 December 2007 <!--DASHBot-->| deadurl= no}}</ref><ref>{{cite web |url=http://news.bbc.co.uk/2/hi/entertainment/7126800.stm |title=Actor Anton Rodgers dies aged 74 |accessdate=2007-12-04 |format= |work=BBC News Online  | date=2007-12-04| archiveurl= http://web.archive.org/web/20071206111432/http://news.bbc.co.uk/2/hi/entertainment/7126800.stm| archivedate= 6 December 2007 <!--DASHBot-->| deadurl= no}}</ref>'''
        self.assertEqual(
            extract_snippets(s), [])

if __name__ == '__main__':
    unittest.main()
