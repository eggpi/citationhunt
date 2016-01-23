#-*- encoding: utf-8 -*-
from __future__ import unicode_literals

import os
os.environ['CH_LANG'] = 'fr'
from base import *
snippet_parser = get_localized_snippet_parser()

import unittest
import functools

# ignore size limits to make these tests
extract_snippets = functools.partial(
    snippet_parser.extract_snippets, minlen = 0, maxlen = float('inf'))

def extract_lead_snippets(text):
    snippets = extract_snippets(text)
    assert snippets[0][0] == ''
    return snippets[0][1]

class ExtractSnippetTest(unittest.TestCase):
    def test_refnec_args(self):
        s = '''En {{refnec|date=mai 2011|1693}}, il fait la connaissance de [[Gottfried Wilhelm Leibniz|Leibniz]].'''
        self.assertEqual(
            extract_lead_snippets(s),
            ['En 1693%s, il fait la connaissance de Leibniz.' %
                CITATION_NEEDED_MARKER])

    def test_phonetique(self):
        s = '''Ce nom de famille se prononce [{{phonétique|dəbʁɔj}}]{{refnec}}'''
        self.assertEqual(
            extract_lead_snippets(s),
            ['Ce nom de famille se prononce [dəbʁɔj]' +
                CITATION_NEEDED_MARKER])

    def test_siecle(self):
        s = '''Il est confondu avec cette lettre jusqu’au {{siècle|xvi}} siècle'''
        self.assertEqual(
            extract_lead_snippets(s + '{{refnec}}'),
            ['Il est confondu avec cette lettre jusqu’au XVIᵉ siècle' +
                CITATION_NEEDED_MARKER])

if __name__ == '__main__':
    unittest.main()
