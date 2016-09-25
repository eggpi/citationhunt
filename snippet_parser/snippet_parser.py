from __future__ import unicode_literals

import os
import sys

_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)

import config
from utils import *

import re
import itertools
import wikitools
import mwparserfromhell
import importlib

from base import matches_any, REF_MARKER, CITATION_NEEDED_MARKER

cfg = config.get_localized_config()
WIKIPEDIA_BASE_URL = 'https://' + cfg.wikipedia_domain
WIKIPEDIA_WIKI_URL = WIKIPEDIA_BASE_URL + '/wiki/'
WIKIPEDIA_API_URL = WIKIPEDIA_BASE_URL + '/w/api.php'

STRIP_REGEXP = re.compile( # strip spaces before the markers
    '\s+(' + CITATION_NEEDED_MARKER + '|' + REF_MARKER + ')')

log = Logger()

import os
sys.path.append(os.path.dirname(__file__))
try:
    localized_module = importlib.import_module(cfg.lang_code)
except ImportError:
    log.info('No snippet_parser for lang_code %s, using stub!' % cfg.lang_code)
    localized_module = importlib.import_module('stub')
snippet_parser = localized_module.SnippetParser()

# Used for fast searching in the tokenize function
_lowercase_cn_templates = [
    t.lower() for t in cfg.citation_needed_templates]

def cleanup_snippet(snippet):
    snippet = re.sub(STRIP_REGEXP, r'\1', snippet).strip()
    snippet = re.sub(',\s+\)', ')', snippet)
    snippet = re.sub('\(\)\s', '', snippet)
    snippet = re.sub('\[\]\s', '', snippet)
    return snippet

def fast_parse(wikitext):
    tokenizer = mwparserfromhell.parser.CTokenizer()
    # Passing skip_style_tags helps us get around some builder exceptions,
    # see https://github.com/earwig/mwparserfromhell/issues/40
    tokens = tokenizer.tokenize(wikitext, 0, True)
    # Add a sentinel representing a "end of article" section
    tokens.append(mwparserfromhell.parser.tokens.HeadingStart())

    # Slice the original token stream into a (potentially much smaller) stream
    # consisting only of the tokens in sections that contain citation needed
    # templates. We can then build the parser tree out of those as usual, which
    # is a more expensive operation.
    reduced_tokens = []
    prev_section_idx = 0
    section_has_citation_needed = False
    for i, (t1, t2) in enumerate(zip(tokens, tokens[1:])):
        if isinstance(t2, mwparserfromhell.parser.tokens.HeadingStart):
            if section_has_citation_needed:
                reduced_tokens.extend(tokens[prev_section_idx:i+1])
            prev_section_idx = i+1
            section_has_citation_needed = False

        # We detect a citation needed template by looking at a TemplateOpen
        # token followed by a suitable Text token
        section_has_citation_needed |= (
            isinstance(t1, mwparserfromhell.parser.tokens.TemplateOpen) and
            isinstance(t2, mwparserfromhell.parser.tokens.Text) and
            any(t in t2.text.lower() for t in _lowercase_cn_templates))
    try:
        return mwparserfromhell.parser.Builder().build(reduced_tokens)
    except mwparserfromhell.parser.ParserError:
        return None

def extract_snippets(wikitext, minlen, maxlen):
    """Extracts snippets lacking citations.

    This function looks for snippets of the article that are marked with any of
    the templates in `cfg.citation_needed_templates` from the `wikitext` passed
    as parameter, and returns those that are greater than `minlen` but smaller
    than `maxlen`.

    The return value is a list of lists of the form:
        [
            [<section1>, [<snippet1>, <snippet2>, ...]],
            [<section2>, [<snippet1>, ...]],
            ...
        ]
    """

    snippets = [] # [section, [snippets]]

    wikicode = fast_parse(wikitext)
    if wikicode is None:
        # Fall back to full parsing if fast parsing fails
        wikicode = mwparserfromhell.parse(wikitext)
    sections = wikicode.get_sections(
        include_lead = True, include_headings = True, flat = True)

    for i, section in enumerate(sections):
        assert i == 0 or \
            isinstance(section.get(0), mwparserfromhell.nodes.heading.Heading)
        sectitle = unicode(section.get(0).title.strip()) if i != 0 else ''
        secsnippets = []
        snippets.append([sectitle, secsnippets])

        paragraphs = section.split('\n\n')
        for paragraph in paragraphs:
            # Invoking a string method on a Wikicode object returns a string,
            # so we need to parse it again :(
            wikicode = mwparserfromhell.parse(paragraph)

            blacklisted_tag_or_template = itertools.chain(
                (tag.tag in cfg.tags_blacklist
                    for tag in wikicode.filter_tags()),
                (matches_any(tpl, cfg.templates_blacklist)
                    for tpl in wikicode.filter_templates()),
            )
            if any(blacklisted_tag_or_template):
                continue

            snippet = cleanup_snippet(wikicode.strip_code())
            if '\n' in snippet:
                # Lists cause more 'paragraphs' to be generated
                paragraphs.extend(snippet.split('\n'))
                continue

            if CITATION_NEEDED_MARKER not in snippet:
                # marker may have been inside wiki markup
                continue

            usable_len = (
                len(snippet) -
                (len(CITATION_NEEDED_MARKER) *
                    snippet.count(CITATION_NEEDED_MARKER)) -
                (len(REF_MARKER) *
                    snippet.count(REF_MARKER)))
            if usable_len > maxlen or usable_len < minlen:
                continue
            secsnippets.append(snippet)
    return snippets

def extract_sections(wikitext, minlen=None, maxlen=None):
    """Extracts sections/subsections lacking citations.

    This function looks for sections of the article that are marked with any of
    the templates in `cfg.citation_needed_templates`. The output is meant to be
    converted into HTML by the Wikimedia API.

    The return value is a list of lists of the form:
        [
            [<section1>, [<subsection1>, <subsection2>, ...]],
            [<section2>, [<subsection1>, ...]],
            ...
        ]
    """

    snippets = [] # [section, [snippets]]
    sections = mwparserfromhell.parse(wikitext).get_sections(
        include_lead = True, include_headings = True, flat = True)

    i = 0
    while i < len(sections):
        section = sections[i]
        assert i == 0 or \
            isinstance(section.get(0), mwparserfromhell.nodes.heading.Heading)
        sectitle = unicode(section.get(0).title.strip()) if i != 0 else ''
        seclevel = section.get(0).level if i != 0 else float('inf')
        secsnippets = []
        snippets.append([sectitle, secsnippets])
        i += 1

        for tpl in section.filter_templates():
            if matches_any(tpl, cfg.citation_needed_templates):
                break
        else:
            # This section doesn't need references, move on to the next one
            continue

        # Consume the following sections until we find another one at the
        # same level (or the end of the wikicode). All of that needs references.
        nodes = section.nodes
        while i < len(sections):
            subsection = sections[i]
            if subsection.get(0).level <= seclevel:
                # not really a subsection
                break
            nodes.extend(subsection.nodes)
            i += 1

        if not nodes:
            # weird, looks like this section was really empty!
            continue

        wikicode = mwparserfromhell.parse(
                mwparserfromhell.wikicode.Wikicode(nodes).strip_code())

        # skip the templates that remained at the beginning and end
        empty_or_template = (lambda node:
            node == '' or
            isinstance(node, mwparserfromhell.nodes.template.Template) or
            re.match('^\n+$', e(node)))
        nodes = list(itertools.dropwhile(empty_or_template, wikicode.nodes))
        wikicode.nodes = reversed(list(
            itertools.dropwhile(empty_or_template, nodes[::-1])))
        snippet = cleanup_snippet(unicode(wikicode))

        # Chop off some paragraphs at the end until we're at a reasonable
        # size, since we don't actually display the whole thing in the UI
        snippet = '\n\n'.join(p.strip(' ') for p in snippet.split('\n\n')[:10])
        if snippet:
            # We'll often end up with just a section header here, so hopefully
            # it will be smaller than the minimum size when converted to HTML.
            # FIXME: Maybe this can be detected?
            secsnippets.append(snippet)
    return snippets

if __name__ == '__main__':
    import pprint
    import sys

    title = sys.argv[1]
    wikipedia = wikitools.wiki.Wiki(WIKIPEDIA_API_URL)
    page = wikitools.Page(wikipedia, title)
    wikitext = page.getWikiText()
    pprint.pprint(extract_snippets(wikitext,
        cfg.snippet_min_size, cfg.snippet_max_size))
