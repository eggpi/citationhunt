#-*- encoding: utf-8 -*-
from __future__ import unicode_literals

from core import *

cfg = config.get_localized_config('fr')
cfg.citation_needed_templates.append('refnec')
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

    def test_citation(self):
        s = '''Selon un article paru en 2000 dans le mensuel ''[[Le Monde diplomatique]]''{{refnec}}, {{Citation|Sa tâche consiste généralement à assurer la promotion de l’image de ses clients en France et en Europe}}{{refnec}}.'''
        self.assertEqual(
            extract_lead_snippets(s),
            ['''Selon un article paru en 2000 dans le mensuel Le Monde diplomatique{0}, « Sa tâche consiste généralement à assurer la promotion de l’image de ses clients en France et en Europe »{0}.'''.format(CITATION_NEEDED_MARKER)])

    def test_quand(self):
        s = '''{{Quand|Passage qui nécessite une décennie ou une date plus précise|date=2015}}{{refnec}}'''
        self.assertEqual(
            extract_lead_snippets(s),
            ['Passage qui nécessite une décennie ou une date plus précise' + CITATION_NEEDED_MARKER])

    def test_lesquelles(self):
        s = '''{{lesquelles|Plusieurs instances, gouvernementales ou non, et même religieuses}}, {{refnec|se sont penchées sur la question et ont proposé plusieurs solutions afin de remédier à ce problème}}'''
        self.assertEqual(
            extract_lead_snippets(s),
            ['Plusieurs instances, gouvernementales ou non, et même religieuses, se sont penchées sur la question et ont proposé plusieurs solutions afin de remédier à ce problème' + CITATION_NEEDED_MARKER])

    def test_drapeau(self):
        s = '''{{drapeau|Algérie|1925|taille=50}}{{refnec}}'''
        self.assertEqual(
            extract_lead_snippets(s), ['Algérie' + CITATION_NEEDED_MARKER])

if __name__ == '__main__':
    unittest.main()
