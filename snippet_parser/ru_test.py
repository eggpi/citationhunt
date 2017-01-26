#-*- encoding: utf-8 -*-
from __future__ import unicode_literals

from core import *

cfg = config.get_localized_config('ru')
cfg.citation_needed_templates = ['Нет АИ', 'Нет АИ 2']
cfg.snippet_min_size = 0
cfg.snippet_max_size = float('inf')
snippet_parser = create_snippet_parser(None, cfg)
extract_snippets = snippet_parser.extract_snippets

import unittest
import functools

def extract_lead_snippets(text):
    snippets = extract_snippets(text)
    assert snippets[0][0] == ''
    return snippets[0][1]

class ExtractSnippetTest(unittest.TestCase):
    def test_no_params(self):
        s = 'Трижды Франклин становился банкротом.'
        self.assertEqual(
            extract_lead_snippets(s + '{{ Нет АИ }}'),
            [s + CITATION_NEEDED_MARKER])

    def test_date_params(self):
        s = 'Трижды Франклин становился банкротом.'
        self.assertEqual(
            extract_lead_snippets(s + '{{ Нет АИ |29|12|2002}}'),
            [s + CITATION_NEEDED_MARKER])

    def test_text_no_date_params(self):
        s = 'Трижды Франклин становился'
        self.assertEqual(
            extract_lead_snippets(s + '{{ Нет АИ 2 |банкротом.}}'),
            [s + 'банкротом.' + CITATION_NEEDED_MARKER])

    def test_text_and_date_params(self):
        s = 'Трижды Франклин становился'
        self.assertEqual(
            extract_lead_snippets(s + '{{ Нет АИ 2 |банкротом.|29|12|2002}}'),
            [s + 'банкротом.' + CITATION_NEEDED_MARKER])

if __name__ == '__main__':
    unittest.main()
