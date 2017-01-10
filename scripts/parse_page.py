import os
import sys
_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)

import config
import snippet_parser

import wikitools

import pprint
import subprocess
import sys
import textwrap

def format_html(html):
    lynx = subprocess.Popen(
        'lynx -dump -stdin -assume_charset UTF-8 '
        '-display_charset UTF-8 -width 80', shell = True,
        stdin = subprocess.PIPE, stdout = subprocess.PIPE)
    stdout, _ = lynx.communicate(html.encode('utf-8'))
    if lynx.returncode:
        print >> sys.stderr, 'Failed to render HTML! Do you have lynx?'
        return html
    return stdout.decode('utf-8').strip('\n')

cfg = config.get_localized_config()

WIKIPEDIA_BASE_URL = 'https://' + cfg.wikipedia_domain
WIKIPEDIA_WIKI_URL = WIKIPEDIA_BASE_URL + '/wiki/'
WIKIPEDIA_API_URL = WIKIPEDIA_BASE_URL + '/w/api.php'

if __name__ == '__main__':
    title = sys.argv[1]
    wikipedia = wikitools.wiki.Wiki(WIKIPEDIA_API_URL)
    parser = snippet_parser.create_snippet_parser(wikipedia, cfg)

    page = wikitools.Page(wikipedia, title)
    wikitext = page.getWikiText()
    for section, snippets in parser.extract(wikitext):
        if not snippets: continue
        print 'Section: %s' % section.encode('utf-8')
        for snippet in snippets:
            if cfg.html_snippet:
                print format_html(snippet)
            else:
                print '   ' + '\n   '.join(textwrap.wrap(snippet, 80))
            print '.'
