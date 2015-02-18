#!/usr/bin/env python

import wikitools
import mwparserfromhell

import sys
import sqlite3
import urlparse

WIKIPEDIA_BASE_URL = 'https://en.wikipedia.org'
WIKIPEDIA_WIKI_URL = WIKIPEDIA_BASE_URL + '/wiki/'
WIKIPEDIA_API_URL = WIKIPEDIA_BASE_URL + '/w/api.php'

MARKER = '7b94863f3091b449e6ab04d44cb372a0' # unlikely to be in any article
CITATION_NEEDED_HTML = '<span class="citation-needed">[citation needed]</span>'

def init_db():
    db = sqlite3.connect('citationhunt.sqlite3')
    cursor = db.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cn (snippet text, url text, title text)
    ''')

    return db, cursor

def is_citation_needed(t):
    return t.name.matches('Citation needed') or t.name.matches('cn')

db, cursor = init_db()
wikipedia = wikitools.wiki.Wiki(WIKIPEDIA_API_URL)
category = wikitools.Category(wikipedia, 'All_articles_with_unsourced_statements')
for page in category.getAllMembersGen():
    wikitext = page.getWikiText()

    for paragraph in wikitext.splitlines():
        wikicode = mwparserfromhell.parse(paragraph)

        for t in wikicode.filter_templates():
            if is_citation_needed(t):
                stripped_len = len(wikicode.strip_code())
                if stripped_len > 420 or stripped_len < 50:
                    # TL;DR or too short
                    continue

                # add the marker so we know where the Citation-needed template
                # was, and remove all markup (including the template)
                wikicode.insert_before(t, MARKER)
                snippet = wikicode.strip_code()
                snippet = snippet.replace(MARKER, CITATION_NEEDED_HTML)

                url = WIKIPEDIA_WIKI_URL + urlparse.unquote(page.urltitle)
                url = unicode(url, 'utf-8')

                row = (snippet, url, page.title)
                assert all(type(x) == unicode for x in row)
                try:
                    cursor.execute('''
                        INSERT INTO cn VALUES (?, ?, ?) ''', row)
                    db.commit()
                except:
                    print >>sys.stderr, 'failed to insert %s in the db' % repr(row)

db.close()
