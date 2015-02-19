#!/usr/bin/env python

import chdb

import wikitools
import mwparserfromhell

import sys
import urlparse
import hashlib

WIKIPEDIA_BASE_URL = 'https://en.wikipedia.org'
WIKIPEDIA_WIKI_URL = WIKIPEDIA_BASE_URL + '/wiki/'
WIKIPEDIA_API_URL = WIKIPEDIA_BASE_URL + '/w/api.php'

MARKER = '7b94863f3091b449e6ab04d44cb372a0' # unlikely to be in any article
CITATION_NEEDED_HTML = '<span class="citation-needed">[citation needed]</span>'

# Monkey-patch mwparserfromhell so it strips some templates and tags the way
# we want.
def template_strip(self, normalize, collapse):
    if self.name == 'convert':
        return ' '.join(map(unicode, self.params[:2]))
mwparserfromhell.nodes.Template.__strip__ = template_strip

def tag_strip(self, normalize, collapse):
    if self.tag == 'ref':
        return None
    return self._original_strip(normalize, collapse)
mwparserfromhell.nodes.Tag._original_strip = mwparserfromhell.nodes.Tag.__strip__
mwparserfromhell.nodes.Tag.__strip__ = tag_strip

mwparserfromhell.nodes.Heading.__strip__ = mwparserfromhell.nodes.Node.__strip__

def is_citation_needed(t):
    return t.name.matches('Citation needed') or t.name.matches('cn')

def extract_snippets(wikitext):
    snippets = []

    # FIXME we should only add each paragraph once
    for paragraph in wikitext.split('\n\n'):
        wikicode = mwparserfromhell.parse(paragraph)

        for t in wikicode.filter_templates():
            if is_citation_needed(t):
                stripped_len = len(wikicode.strip_code())
                if stripped_len > 420 or stripped_len < 140:
                    # TL;DR or too short
                    continue

                # add the marker so we know where the Citation-needed template
                # was, and remove all markup (including the template)
                wikicode.insert_before(t, MARKER)
                snippet = wikicode.strip_code()
                snippet = snippet.replace(MARKER, CITATION_NEEDED_HTML)
                snippets.append(snippet)

    return snippets

def reload_snippets(db):
    cursor = db.cursor()
    wikipedia = wikitools.wiki.Wiki(WIKIPEDIA_API_URL)
    category = wikitools.Category(wikipedia, 'All_articles_with_unsourced_statements')
    for n, page in enumerate(category.getAllMembersGen()):
        wikitext = page.getWikiText()
        snippets = extract_snippets(wikitext)

        for s in snippets:
            url = WIKIPEDIA_WIKI_URL + urlparse.unquote(page.urltitle)
            url = unicode(url, 'utf-8')
            id = unicode(hashlib.sha1(s.encode('utf-8')).hexdigest()[:2*8])

            row = (id, s, url, page.title)
            assert all(type(x) == unicode for x in row)
            try:
                cursor.execute('''
                    INSERT INTO cn VALUES (?, ?, ?, ?) ''', row)
                db.commit()
            except:
                print >>sys.stderr, 'failed to insert %s in the db' % repr(row)

        if n % 100 == 0:
            print '\rprocessed %d pages' % n,

if __name__ == '__main__':
    db = chdb.init_db()
    reload_snippets(db)
    db.close()
