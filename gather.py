#!/usr/bin/env python

import wikitools
import mwparserfromhell

import sys
import sqlite3
import urlparse

WIKIPEDIA_BASE_URL = 'https://en.wikipedia.org'
WIKIPEDIA_WIKI_URL = WIKIPEDIA_BASE_URL + '/wiki/'
WIKIPEDIA_API_URL = WIKIPEDIA_BASE_URL + '/w/api.php'

wikipedia = wikitools.wiki.Wiki(WIKIPEDIA_API_URL)
category = wikitools.Category(wikipedia, 'All_articles_with_unsourced_statements')
marker = '7b94863f3091b449e6ab04d44cb372a0' # unlikely to be in any article
citation_needed_html = '<span class="citation-needed">[citation needed]</span>'

db = sqlite3.connect('citationhunt.sqlite3')
cursor = db.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS cn (snippet text, url text, title text)
''')

for page in category.getAllMembersGen():
    wikitext = page.getWikiText()

    for paragraph in wikitext.splitlines():
        wikicode = mwparserfromhell.parse(paragraph)

        for t in wikicode.filter_templates():
            if t.name.matches('cn') or t.name.matches('Citation needed'):
                wikicode.insert_before(t, marker)
                snippet = wikicode.strip_code()
                if len(snippet) > 420: # 3 tweets
                    # TL;DR
                    continue

                snippet = snippet.replace(marker, citation_needed_html)
                assert type(snippet) == unicode

                url = WIKIPEDIA_WIKI_URL + urlparse.unquote(page.urltitle)
                url = unicode(url, 'utf-8')
                assert type(url) == unicode
                assert type(page.title) == unicode

                row = (snippet, url, page.title)
                try:
                    cursor.execute('''
                        INSERT INTO cn VALUES (?, ?, ?) ''', row)
                    db.commit()
                except:
                    print >>sys.stderr, 'failed to insert %s in the db' % repr(row)

db.close()
