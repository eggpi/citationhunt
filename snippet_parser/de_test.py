#-*- encoding: utf-8 -*-
from __future__ import unicode_literals

from core import *
cfg = config.get_localized_config('de')
cfg.citation_needed_templates.append('Quellen')
snippet_parser = create_snippet_parser(None, config.get_localized_config('de'))

import unittest
import functools

# ignore size limits to make these tests
extract_sections = functools.partial(
    snippet_parser.extract_sections, minlen = 0, maxlen = float('inf'))

def extract_lead_snippets(text):
    snippets = extract_sections('{{Belege fehlen}}\n' + text)
    assert snippets[0][0] == ''
    return snippets[0][1][0]

class ExtractSnippetTest(unittest.TestCase):
    def test_keep_some_tags(self):
        s = """We want to keep '''bold''' and ''italics''."""
        self.assertEqual(extract_lead_snippets(s), s)

    def test_remove_tags(self):
        s = '<gallery>This should be dropped.</gallery> This should not'
        self.assertEqual(extract_lead_snippets(s), 'This should not')

    def test_markup_inside_tag(self):
        s = "''We should strip [[links]] inside tags''"
        self.assertEqual(extract_lead_snippets(s),
                "''We should strip links inside tags''")

    def test_keep_templates(self):
        s = '''Jassir Arafat {{arF|d=Abū ʿAmmār|أبو عمّار}}.'''
        self.assertEqual(extract_lead_snippets(s), s)

    def test_remove_extra_templates_before(self):
        s = '{{Infobox}}\n{{Neutralität}}\n{{Belege fehlen}}\n[[Datei:X.jpb]]\nAll but this text should be removed.{{Taxobox}}'
        self.assertEqual(extract_lead_snippets(s), 'All but this text should be removed.')

    def test_remove_cn_template_in_text(self):
        s = 'Here is some text.\n\n{{Belege fehlen}} Template must go.'
        self.assertEqual(extract_lead_snippets(s), 'Here is some text.\n\nTemplate must go.')

    def test_keep_subsections(self):
        s = '== Section ==\n\n{{Quellen}}\n=== Subsection ===\n\nSome text'
        self.assertEqual(
            extract_sections(s), [
            ['', []],
            ['Section', ["'''Subsection'''\n\nSome text"]]
            ])

    def test_use_subsections(self):
        s = '== Section ==\n\nA lot of text.\n=== Subsection ===\n\n{{ Quellen }}\nSome text'
        self.assertEqual(
            extract_sections(s), [
                ['', []],
                ['Section', []],
                ['Subsection', ["'''Subsection'''\n\nSome text"]]
            ])

    def test_identify_sections(self):
        s = '== Section1 ==\n\n{{Quellen}}\n=== Subsection ===\n\nSome text\n== Section2 ==\n\nMore text.'
        self.assertEqual(
            extract_sections(s), [
            ['', []],
            ['Section1', ["'''Subsection'''\n\nSome text"]],
            ['Section2', []]
            ])

    def test_infobox(self):
        s = '{{Quellen}}{{ Infobox Band }}Some text.'
        self.assertEqual(extract_lead_snippets(s), 'Some text.')


if __name__ == '__main__':
    unittest.main()
