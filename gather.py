#!/usr/bin/env python

import flask
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

def init_db():
    db = sqlite3.connect('citationhunt.sqlite3')
    cursor = db.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cn (snippet text, url text, title text)
    ''')

    return db

def get_db():
    db = getattr(flask.g, '_db', None)
    if db is None:
        db = flask.g._db = init_db()
    return db

def is_citation_needed(t):
    return t.name.matches('Citation needed') or t.name.matches('cn')

def reload_snippets(db):
    cursor = db.cursor()
    wikipedia = wikitools.wiki.Wiki(WIKIPEDIA_API_URL)
    category = wikitools.Category(wikipedia, 'All_articles_with_unsourced_statements')
    for page in category.getAllMembersGen():
        wikitext = page.getWikiText()

        # FIXME we should only add each paragraph once
        for paragraph in wikitext.splitlines():
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

def select_random_snippet():
    cursor = get_db().cursor()
    cursor.execute('''
        SELECT snippet, url, title FROM cn ORDER BY RANDOM() LIMIT 1;''')
    return cursor.fetchone()

app = flask.Flask(__name__)

@app.route('/')
def citation_hunt():
    s, u, t = select_random_snippet()
    return flask.render_template('index.html', snippet = s, url = u, title = t)

@app.teardown_appcontext
def close_db(exception):
    db = getattr(flask.g, '_db', None)
    if db is not None:
        db.close()

if __name__ == '__main__':
    app.run(debug = True)
