#!/usr/bin/env python

'''
Parse a single page and display the snippets found in it.

Make sure to set the CH_LANG environment variable before invoking this script.

Usage:
    parse_page.py <title_or_pageid> [--output=<output>]

Options:
    output    'raw' or 'html' (inferred from the config if not passed)
'''

from __future__ import unicode_literals

import os
import sys
_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)

import config
import snippet_parser

import docopt
import wikitools

import pprint
import subprocess
import sys
import textwrap

def _print(str):
    print str.encode('utf-8')

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

if __name__ == '__main__':
    arguments = docopt.docopt(__doc__)
    cfg = config.get_localized_config()

    WIKIPEDIA_BASE_URL = 'https://' + cfg.wikipedia_domain
    WIKIPEDIA_WIKI_URL = WIKIPEDIA_BASE_URL + '/wiki/'
    WIKIPEDIA_API_URL = WIKIPEDIA_BASE_URL + '/w/api.php'

    wikipedia = wikitools.wiki.Wiki(WIKIPEDIA_API_URL)
    parser = snippet_parser.create_snippet_parser(wikipedia, cfg)

    try:
        int(arguments['<title_or_pageid>'])
        page = wikitools.Page(
            wikipedia, pageid = int(arguments['<title_or_pageid>']))
    except:
        page = wikitools.Page(
            wikipedia, title = arguments['<title_or_pageid>'])

    wikitext = page.getWikiText()
    for section, snippets in parser.extract(wikitext):
        if not snippets: continue
        _print('Section: %s' % section)
        for snippet in snippets:
            if cfg.html_snippet and arguments['--output'] != 'raw':
                output = format_html(snippet)
            else:
                output = '   ' + '\n   '.join(textwrap.wrap(snippet, 80))
            _print(output)
            _print('.')
