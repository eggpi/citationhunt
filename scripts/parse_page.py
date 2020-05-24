#!/usr/bin/env python3

'''
Parse a single page and display the snippets found in it.

Make sure to set the CH_LANG environment variable before invoking this script.

Usage:
    parse_page.py <title_or_pageid> [--output=<output>]

Options:
    output    'raw' or 'html' (inferred from the config if not passed)
'''



import os
import sys
_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)

import config
import yamwapi as mwapi
import snippet_parser

import docopt

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
        print('Failed to render HTML! Do you have lynx?', file=sys.stderr)
        return html
    return stdout.decode('utf-8').strip('\n')

if __name__ == '__main__':
    arguments = docopt.docopt(__doc__)
    cfg = config.get_localized_config()

    WIKIPEDIA_BASE_URL = 'https://' + cfg.wikipedia_domain
    WIKIPEDIA_WIKI_URL = WIKIPEDIA_BASE_URL + '/wiki/'
    WIKIPEDIA_API_URL = WIKIPEDIA_BASE_URL + '/w/api.php'

    wikipedia = mwapi.MediaWikiAPI(WIKIPEDIA_API_URL, cfg.user_agent)
    parser = snippet_parser.create_snippet_parser(wikipedia, cfg)

    try:
        int(arguments['<title_or_pageid>'])
        wikitext = wikipedia.get_page_contents(
            pageid = int(arguments['<title_or_pageid>']))
    except:
        wikitext = wikipedia.get_page_contents(
            title = arguments['<title_or_pageid>'])

    for snippet in parser.extract(wikitext):
        print('Section: %s' % snippet.section)
        if arguments['--output'] != 'raw':
            output = format_html(snippet.snippet)
        else:
            output = '   ' + '\n   '.join(
                textwrap.wrap(snippet.snippet, 80, break_long_words = False))
        print(output)
        print('. dates = {}'.format(
            [d.strftime('%B %Y') for d in snippet.dates]))
