#!/usr/bin/env python3

import os
import sys

_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)

import config
from . import lxml_utils
from . import stats
from utils import *

import mwparserfromhell
import lxml.html
import lxml.etree
import lxml.cssselect

import datetime
import io as StringIO
import itertools
from copy import copy

SNIPPET_WRAPPER_CLASS = 'ch-snippet'

CITATION_NEEDED_MARKER_CLASS = 'ch-cn-marker'
_TEMPLATE_ID_ATTR = 'data-id'
_CITATION_NEEDED_MARKER_MARKUP = (
    '<span class="%s" %s="{tpl_id}">{tpl}</span>' % \
        (CITATION_NEEDED_MARKER_CLASS, _TEMPLATE_ID_ATTR))

_LIST_TAGS = set(['ol', 'ul'])
_SNIPPET_ROOT_TAGS = set(['p']) | _LIST_TAGS

class Snippet:
    '''Holder object for a snippet.

    section (str) is the title of the section where the snippet is.
    text (str) is the HTML string for the snippet.
    dates (datetime.datetime) are the dates in the citation needed templates
          found in the snippet, sorted ascending.
    '''

    __slots__ = ('section', 'snippet', 'dates')

    def __init__(self):
        self.section = None
        self.snippet = None
        self.dates = []

    def __eq__(self, other):
        return self.section == other.section and self.snippet == other.snippet

    def __hash__(self):
        return hash((self.section, self.snippet))

class SnippetParser:
    '''Turn wikitext into HTML snippets for Citation Hunt.'''

    def __init__(self, wikipedia, cfg):
        self._cfg = cfg
        self._wikipedia = wikipedia

        self._lowercase_cn_templates = set(
            t.lower() for t in self._cfg.citation_needed_templates)
        assert len(self._lowercase_cn_templates) > 0

        self._html_css_selectors_to_strip = [
            lxml.cssselect.CSSSelector(css_selector)
            for css_selector in self._cfg.html_css_selectors_to_strip
        ]

        self.stats = stats.SnippetParserStats()

    def _get_date_from_template(self, tpl):
        if self._cfg.lang_code != 'en':
            return None
        try:
            return datetime.datetime.strptime(
                tpl.get('date').split('=', 1)[1], '%B %Y')
        except ValueError:
            return None

    # Separate method for testing.
    def _make_template_id(self, section, template):
        return f'section-{section}-template-{template}'

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

        The return value is a list of Snippet objects.
        """

        wikicode = self._fast_parse(wikitext)
        if wikicode is None:
            # Fall back to full parsing if fast parsing fails
            wikicode = mwparserfromhell.parse(wikitext)
        sections = wikicode.get_sections(
            include_lead = True, include_headings = True, flat = True)

        # Whatever data we want to extract from the templates as wikitext and
        # use once they are (potentially) turned into snippets after HTML
        # expansion. We tag templates with a key into this dict before
        # converting to HTML, then we can extract the key from the HTML that
        # is returned.
        template_data = {}

        snippets = []
        minlen, maxlen = self._cfg.snippet_min_size, self._cfg.snippet_max_size
        for i, section in enumerate(sections):
            # First, do a pass over the templates to check whether we have
            # citation needed templates in this section (this should always be
            # true when _fast_parse succeeds above), and replace them with our
            # markers.
            has_citation_needed_template = False
            for j, tpl in enumerate(section.filter_templates()):
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
                    tpl_id = self._make_template_id(i, j)
                    template_data[tpl_id] = self._get_date_from_template(tpl)
                    marked = _CITATION_NEEDED_MARKER_MARKUP.format(
                        tpl_id = tpl_id, tpl = tpl)
                    try:
                        section.replace(tpl, marked)
                    except ValueError:
                        # This seems to be caused by citation needed templates
                        # inside the parameters of other citation needed
                        # templates. Since this doesn't look particularly
                        # frequent, just swallow the error here.
                        # TODO: Get some stats on how often this happens, log it
                        return []
            if not has_citation_needed_template: continue

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
                    text = str(section), **self._cfg.html_parse_parameters)
                html = self._wikipedia.parse(params)['parse']['text']['*']
            except:
                continue

            tree = lxml.html.parse(
                StringIO.StringIO(html),
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
                        snippet_roots.extend(self._html_list_to_snippets(root))
                    else:
                        snippet_roots.append(self._make_snippet_root(root))
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
                snippet = Snippet()

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
                    tpl_id = marker.attrib[_TEMPLATE_ID_ATTR]
                    if template_data.get(tpl_id) is not None:
                        snippet.dates = sorted(snippet.dates +
                            [template_data[tpl_id]])
                    del marker.attrib[_TEMPLATE_ID_ATTR]
                    lxml_utils.strip_space_before_element(marker)

                length = len(sr.text_content().strip())
                self.stats.snippet_lengths[length] += 1
                if minlen < length < maxlen:
                    snippet.snippet = d(lxml.html.tostring(
                        sr, encoding = 'utf-8', method = 'html')).strip()
                    snippets_in_section.add(snippet)

            sectitle = ''
            if i != 0:
                # Re-parse the section title because fast_parse is
                # configured to ignore style tags (see above and
                # https://github.com/earwig/mwparserfromhell/issues/40),
                # but we do want to remove them now with strip_code().
                sectitle = mwparserfromhell.parse(
                    str(section.get(0).title).strip()).strip_code()
            for snippet in snippets_in_section:
                snippet.section = sectitle
                snippets.append(snippet)
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
