#!/usr/bin/env python

from __future__ import unicode_literals
import os
import sys

_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)

import config
import lxml_utils
import stats
from utils import *

import mwparserfromhell
import lxml.html
import lxml.etree
import lxml.cssselect

import cStringIO as StringIO
import itertools
from copy import copy

SNIPPET_WRAPPER_CLASS = 'ch-snippet'

CITATION_NEEDED_MARKER_CLASS = 'ch-cn-marker'
_CITATION_NEEDED_MARKER_MARKUP = (
    '<span class="%s">{tpl}</span>' % CITATION_NEEDED_MARKER_CLASS)

_LIST_TAGS = set(['ol', 'ul'])
_SNIPPET_ROOT_TAGS = set(['p']) | _LIST_TAGS

class SnippetParser(object):
    '''A base class for snippet parsers in various languages.'''

    def __init__(self, wikipedia, cfg):
        self._cfg = cfg
        self._wikipedia = wikipedia

        self._lowercase_cn_templates = set(
            t.lower() for t in self._resolve_redirects_to_templates(
                self._cfg.citation_needed_templates))
        assert len(self._lowercase_cn_templates) > 0

        self._html_css_selectors_to_strip = [
            lxml.cssselect.CSSSelector(css_selector)
            for css_selector in self._cfg.html_css_selectors_to_strip
        ]

        self.stats = stats.SnippetParserStats()

    def _resolve_redirects_to_templates(self, templates):
        templates = set(templates)
        params = {
            'prop': 'redirects',
            'titles': '|'.join(
                # The API resolves Template: to the relevant per-language prefix
                'Template:' + tplname
                for tplname in self._cfg.citation_needed_templates
            ),
            'rnamespace': 10,
        }
        for result in self._wikipedia.query(params):
            # We could fall back to just using self._cfg.citation_needed_templates
            # if the API request fails, but for now let's just crash
            for page in result['query']['pages'].values():
                for redirect in page.get('redirects', []):
                    # TODO We technically only need to keep the templates that
                    # mwparserfromhell will consider different from one another
                    # (e.g., no need to have both Cn and CN)
                    if ':' not in redirect['title']:
                        # Not a template?
                        continue
                    tplname = redirect['title'].split(':', 1)[1]
                    templates.add(tplname)
        return templates

    def _fast_parse(self, wikitext):
        tokenizer = mwparserfromhell.parser.CTokenizer()
        try:
            # Passing skip_style_tags helps us get around some builder exceptions,
            # see https://github.com/earwig/mwparserfromhell/issues/40
            tokens = tokenizer.tokenize(wikitext, 0, True)
        except SystemError:
            # FIXME This happens sometimes on Tools Labs, why?
            return None

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
                t2.text.lower().strip() in self._lowercase_cn_templates)
        try:
            return mwparserfromhell.parser.Builder().build(reduced_tokens)
        except mwparserfromhell.parser.ParserError:
            return None

    def extract(self, wikitext):
        """
        This is the main method for extracting HTML snippets out of wiki markup.

        Broadly, the algorithm goes as follows:
            1) Find the sections that contain any of the citation needed
               templates.
            2) Mark the templates with a special element CITATION_NEEDED_MARKER.
            3) Use the Parse API to convert the sections to HTML.
            4) Cleanup the HTML by removing certain kinds of elements
               (such as tables) that we don't know how to handle.
            5) Find the markers inserted in step 2, then climb up the HTML tree
               starting at them until we find a suitable parent element to form
               a snippet (_SNIPPET_ROOT_TAGS)
            6) Check whether the final length of the (text content of the)
               snippet is within the bounds we're willing to accept, and if so,
               use it.

        The return value is a list of lists of the form:
            [
                [<section1>, [<snippet1>, <snippet2>, ...]],
                [<section2>, [<snippet1>, ...]],
                ...
            ]
        """

        wikicode = self._fast_parse(wikitext)
        if wikicode is None:
            # Fall back to full parsing if fast parsing fails
            wikicode = mwparserfromhell.parse(wikitext)
        sections = wikicode.get_sections(
            include_lead = True, include_headings = True, flat = True)

        snippets = []
        minlen, maxlen = self._cfg.snippet_min_size, self._cfg.snippet_max_size
        for i, section in enumerate(sections):
            # First, do a pass over the templates to check whether we have a
            # citation needed template in this section. This should always be true
            # when _fast_parse succeeds above.
            has_citation_needed_template = False
            for tpl in section.filter_templates():
                # Make sure to use index-named parameters for all templates.
                # That's because later on we'll insert a marker tag around citation
                # needed templates, and that marker contains a '=', which can
                # confuse the parser if the template is inside the parameters of
                # another template (yes, that can happen).
                # Making sure all parameters are index-named is the workaround
                # proposed in https://phabricator.wikimedia.org/T16235
                for param in tpl.params:
                    param.showkey = True
                if self._is_citation_needed(tpl):
                    has_citation_needed_template = True
            if not has_citation_needed_template: continue

            # Now do another pass to actually insert our markers.
            for tpl in section.filter_templates():
                if self._is_citation_needed(tpl):
                    marked = _CITATION_NEEDED_MARKER_MARKUP.format(tpl = tpl)
                    try:
                        section.replace(tpl, marked)
                    except ValueError:
                        # This seems to be caused by citation needed templates
                        # inside the parameters of other citation needed
                        # templates. Since this doesn't look particularly
                        # frequent, just swallow the error here.
                        # TODO Get some stats on how often this happens, log it
                        return []

            # Reference groups can cause an error message to be
            # generated directly in the output HTML, remove them.
            for ref in section.filter_tags(matches = lambda t: t.tag == 'ref'):
                if ref.has('group'):
                    ref.remove('group')

            # Note: we could gain a little speedup here by breaking the section
            # into paragraphs and taking only the paragraphs we want before
            # sending them for parsing, but that's trickier than it looks,
            # since paragraph breaks can happen not just due to '\n\n', and
            # even within template parameters!

            try:
                params = dict(
                    text = unicode(section), **self._cfg.html_parse_parameters)
                html = self._wikipedia.parse(params)['parse']['text']['*']
            except:
                continue

            tree = lxml.html.parse(
                StringIO.StringIO(e(html)),
                parser = lxml.html.HTMLParser(
                    encoding = 'utf-8', remove_comments = True)).getroot()
            if tree is None: continue

            for strip_selector in self._html_css_selectors_to_strip:
                for element in strip_selector(tree):
                    # Make sure we don't remove elements inside the markers.
                    # For a few Wikipedias (Chinese, Russian) the expansion of
                    # {{fact}} is marked as .noprint, which we otherwise want
                    # to remove.
                    inside_marker = any(
                        e.attrib.get('class') == CITATION_NEEDED_MARKER_CLASS
                        for e in element.iterancestors('span'))
                    if not inside_marker:
                        lxml_utils.remove_element(element)

            snippet_roots = []
            if self._cfg.extract == 'snippet':
                # We climb up from each marker to the nearest antecessor element
                # that we can use as a snippet.
                for marker in tree.cssselect('.' + CITATION_NEEDED_MARKER_CLASS):
                    root = marker.getparent()
                    while root is not None and root.tag not in _SNIPPET_ROOT_TAGS:
                        root = root.getparent()
                    if root is None:
                        continue
                    if root.tag in _LIST_TAGS:
                        snippet_roots = self._html_list_to_snippets(root)
                    else:
                        snippet_roots = [self._make_snippet_root(root)]
            else:
                # Throw away the actual template, we don't need it.
                for marker in tree.cssselect('.' + CITATION_NEEDED_MARKER_CLASS):
                    lxml_utils.remove_element(marker)

                # Keep only snippet root top-level elements within the body
                # that have any text content (we may have created empty elements
                # above during cleanup). This is not great as any content within,
                # say, <blockquote> gets removed entirely, but it's good enough
                # in most cases.
                snippet_roots = [
                    self._make_snippet_root(*(
                        e for e in tree.cssselect(
                            'body > ' + ', '.join(_SNIPPET_ROOT_TAGS))
                        if e.text_content() and not e.text_content().isspace()))
                ]

            snippets_in_section = set()
            for sr in snippet_roots:
                # Some last-minute cleanup to shrink the snippet some more.
                # Remove links and attributes, but make sure to keep the
                # class in our marker elements, and that there is no space
                # before it (which we need for the UI).
                lxml.etree.strip_tags(sr, 'a')
                markers_in_snippet = sr.cssselect(
                    '.' + CITATION_NEEDED_MARKER_CLASS)
                lxml.etree.strip_attributes(sr, 'id', 'class', 'style')
                sr.attrib['class'] = SNIPPET_WRAPPER_CLASS
                for marker in markers_in_snippet:
                    marker.attrib['class'] = CITATION_NEEDED_MARKER_CLASS
                    lxml_utils.strip_space_before_element(marker)

                length = len(sr.text_content().strip())
                self.stats.snippet_lengths[length] += 1
                if minlen < length < maxlen:
                    snippet = d(lxml.html.tostring(
                        sr, encoding = 'utf-8', method = 'html')).strip()
                    snippets_in_section.add(snippet)

            sectitle = unicode(section.get(0).title.strip()) if i != 0 else ''
            snippets.append([sectitle, list(snippets_in_section)])
        return snippets

    def _make_snippet_root(self, *child_elements):
        root = lxml.html.Element('div')
        root.extend(copy(e) for e in child_elements)
        return root

    def _html_list_to_snippets(self, list_element):
        """
        Given a list element containing a citation needed marker in one of
        its <li>, extract a snippet by taking the <li> with the marker plus
        a couple of other <li> for context, dropping all other items.

        Returns a list of snippets extracted from the input list element.
        """

        # Try to take the preceding paragraph, if any.
        # TODO Also take <dl>, <h2> and <h3>?
        preamble = [
            e for e in itertools.islice(
                list_element.itersiblings(preceding = True), 1)
            if e.tag == 'p'
        ]
        lis_with_marker = list(list_element.xpath(
            # We define a path containing the marker elements with <li>
            # ancestors, then use the ancestor::li[1] construct to select
            # the <li> rather than the marker itself - the <li> will be
            # the first ancestor of the marker.
            './/li/descendant::*[@class="%s"]/ancestor::li[1]' % (
                CITATION_NEEDED_MARKER_CLASS)))
        snippet_roots = []
        for li_with_marker in lis_with_marker:
            sr = self._make_snippet_root(*preamble)
            sr.append(lxml.html.Element(list_element.tag))

            # Try to take one <li> before and one after the one we want, but
            # don't if they have nested lists in them, as that typically makes
            # the snippet too large.
            for before in li_with_marker.itersiblings('li', preceding = True):
                if not before.cssselect(', '.join(_LIST_TAGS)):
                    sr[-1].append(copy(before))
                break
            sr[-1].append(copy(li_with_marker))
            for after in li_with_marker.itersiblings('li'):
                if not after.cssselect(', '.join(_LIST_TAGS)):
                    sr[-1].append(copy(after))
                break
            snippet_roots.append(sr)
        return snippet_roots

    def _is_citation_needed(self, template):
        return template.name.lower().strip() in self._lowercase_cn_templates

def create_snippet_parser(wikipedia, cfg):
    return SnippetParser(wikipedia, cfg)
