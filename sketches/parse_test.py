import wikitools
import mwparserfromhell
import urlparse

WIKIPEDIA_BASE_URL = 'https://en.wikipedia.org'
WIKIPEDIA_WIKI_URL = WIKIPEDIA_BASE_URL + '/wiki/'
WIKIPEDIA_API_URL = WIKIPEDIA_BASE_URL + '/w/api.php'
MARKER = '7b94863f3091b449e6ab04d44cb372a0' # unlikely to be in any article

PAGE_TITLE = '12_Miles_of_Bad_Road'
CACHE_FILE = 'parsetest.cache'

def is_citation_needed(t):
    return t.name.matches('Citation needed') or t.name.matches('cn')

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

try:
    with open(CACHE_FILE) as cache:
        wikitext = cache.read()
except:
    wikipedia = wikitools.wiki.Wiki(WIKIPEDIA_API_URL)
    page = wikitools.Page(wikipedia, title = PAGE_TITLE)
    wikitext = page.getWikiText()

    with open(CACHE_FILE, 'w') as cache:
        cache.write(wikitext)

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
            print snippet
            print '----'
