#!/usr/bin/env python

from __future__ import unicode_literals

from utils import *

import wikitools
import mwparserfromhell

import re
import sys
import urlparse
import hashlib

WIKIPEDIA_BASE_URL = 'https://en.wikipedia.org'
WIKIPEDIA_WIKI_URL = WIKIPEDIA_BASE_URL + '/wiki/'
WIKIPEDIA_API_URL = WIKIPEDIA_BASE_URL + '/w/api.php'

REF_MARKER = 'ec5b89dc49c433a9521a13928c032129'
CITATION_NEEDED_MARKER = '7b94863f3091b449e6ab04d44cb372a0'

TEST_WIKITEXT_CACHE_FILENAME = '.test-wikitext.cache'

# Monkey-patch mwparserfromhell so it strips some templates and tags the way
# we want.
def template_strip(self, normalize, collapse):
    if self.name.matches('convert'):
        return ' '.join(map(unicode, self.params[:2]))
mwparserfromhell.nodes.Template.__strip__ = template_strip

def tag_strip(self, normalize, collapse):
    if self.tag == 'ref':
        return REF_MARKER
    return self._original_strip(normalize, collapse)
mwparserfromhell.nodes.Tag._original_strip = mwparserfromhell.nodes.Tag.__strip__
mwparserfromhell.nodes.Tag.__strip__ = tag_strip

mwparserfromhell.nodes.Heading.__strip__ = mwparserfromhell.nodes.Node.__strip__

def wikilink_strip(self, normalize, collapse):
    if self.title.startswith('File:'):
        return ''
    return self._original_strip(normalize, collapse)
mwparserfromhell.nodes.Wikilink._original_strip = \
    mwparserfromhell.nodes.Wikilink.__strip__
mwparserfromhell.nodes.Wikilink.__strip__ = wikilink_strip

def is_citation_needed(t):
    return t.name.matches('Citation needed') or t.name.matches('cn')

def extract_snippets(wikitext, minlen = 140, maxlen = 420, is_lead = False):
    snippets = [] # [section, [snippets]]
    strip_regexp = re.compile( # strip spaces before the markers
        '\s+(' + CITATION_NEEDED_MARKER + '|' + REF_MARKER + ')')

    sections = mwparserfromhell.parse(wikitext).get_sections(
        include_lead = True, include_headings = True, flat = True)
    assert ''.join(unicode(s) for s in sections) == d(wikitext)

    for i, section in enumerate(sections):
        assert i == 0 or \
            isinstance(section.get(0), mwparserfromhell.nodes.heading.Heading)
        sectitle = unicode(section.get(0).title.strip()) if i != 0 else ''
        secsnippets = []
        snippets.append([sectitle, secsnippets])

        for paragraph in section.split('\n\n'):
            wikicode = mwparserfromhell.parse(paragraph)

            for t in wikicode.filter_templates():
                if is_citation_needed(t):
                    stripped_len = len(wikicode.strip_code())
                    if stripped_len > maxlen or stripped_len < minlen:
                        # TL;DR or too short
                        continue

                    # add the marker so we know where the Citation-needed
                    # template was
                    wikicode.insert_before(t, CITATION_NEEDED_MARKER)

            snippet = re.sub(strip_regexp, r'\1',
                wikicode.strip_code())
            if CITATION_NEEDED_MARKER in snippet:
                # marker may have been inside wiki markup
                secsnippets.append(snippet)
    return snippets

if __name__ == '__main__':
    import pprint

    title = sys.argv[1]
    wikitext = None
    try:
        with open(TEST_WIKITEXT_CACHE_FILENAME, 'r') as cache:
            if cache.readline()[:-1] == title:
                wikitext = cache.read()
    except:
        pass
    finally:
        if wikitext is None:
            wikipedia = wikitools.wiki.Wiki(WIKIPEDIA_API_URL)
            page = wikitools.Page(wikipedia, title)
            wikitext = page.getWikiText()

    with open(TEST_WIKITEXT_CACHE_FILENAME, 'w') as cache:
        print >>cache, title
        cache.write(wikitext)

    pprint.pprint(extract_snippets(wikitext))
