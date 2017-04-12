#!/usr/bin/env python

from __future__ import unicode_literals
import os
import sys

_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)

import config
from utils import *

import mwparserfromhell
import lxml.html
import lxml.etree
import lxml.cssselect

import cStringIO as StringIO
import re
import importlib
import itertools
from copy import copy

REF_MARKER = 'ec5b89dc49c433a9521a139'
CITATION_NEEDED_MARKER = '7b94863f3091b449e6ab04d4'

STRIP_REGEXP = re.compile( # strip spaces before the markers
    '\s+(' + CITATION_NEEDED_MARKER + '|' + REF_MARKER + ')')

def matches_any(template, names):
    return any(template.name.matches(n) for n in names)

CITATION_NEEDED_MARKER_CLASS = 'ch-cn-marker'
_CITATION_NEEDED_MARKER_MARKUP = (
    '<span class="%s">%%s</span>' % CITATION_NEEDED_MARKER_CLASS)

class SnippetParserBase(object):
    '''A base class for snippet parsers in various languages.'''

    def __init__(self, wikipedia, cfg):
        self._cfg = cfg
        self._wikipedia = wikipedia

        self._strip_methods = {
            mwparserfromhell.nodes.Template: self.strip_template,
            mwparserfromhell.nodes.Tag: self.strip_tag,
            mwparserfromhell.nodes.Wikilink: self.strip_wikilink,
            mwparserfromhell.nodes.Heading: self.strip_heading,
        }

        self._lowercase_cn_templates = set(
            t.lower() for t in self._resolve_redirects_to_templates(
                self._cfg.citation_needed_templates))
        assert len(self._lowercase_cn_templates) > 0

        self._html_css_selectors_to_strip = [
            lxml.cssselect.CSSSelector(css_selector)
            for css_selector in self._cfg.html_css_selectors_to_strip
        ]

    def _resolve_redirects_to_templates(self, templates):
        templates = set(templates)
        if self._wikipedia is None:
            # Testing
            return templates
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

    def extract_html_snippets(self, wikitext):
        """
        This is the main method for extracting HTML snippets out of wiki markup.

        Broadly, the algorithm goes as follows:
            1) Find the sections that contain any of the citation needed
               templates.
            2) Mark the templates with a <span> element in each section.
            3) Use the Parse API to convert the sections to HTML.
            4) Cleanup the HTML by removing certain kinds of elements
               (such as tables) that we don't know how to handle.
            5) Find the markers inserted in step 2, then climb up the HTML tree
               starting at them until we find a suitable parent element to form
               a snippet (usually a <p>)
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
            # First, do a pass over the templates to check whether we actually
            # have a citation needed template in this section.
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
                if self.is_citation_needed(tpl):
                    has_citation_needed_template = True
            if not has_citation_needed_template: continue

            # Now do another pass to actually insert our markers.
            for tpl in section.filter_templates():
                if self.is_citation_needed(tpl):
                    marked = _CITATION_NEEDED_MARKER_MARKUP % unicode(tpl)
                    try:
                        section.replace(tpl, marked)
                    except ValueError:
                        # This seems to be caused by citation needed templates
                        # inside the parameters of other citation needed
                        # templates. Since this doesn't look particularly
                        # frequent, just swallow the error here.
                        # TODO Get some stats on how often this happens, log it
                        return []

            for ref in section.filter_tags('ref'):
                if ref.has('group'):
                    # Reference groups can cause an error message to be
                    # generated directly in the output HTML, remove them.
                    ref.remove('group')

            # Note: we could gain a little speedup here by breaking the section
            # into paragraphs and taking only the paragraphs we want before
            # sending them for parsing, but that's trickier than it looks,
            # since paragraph breaks can happen not just doe to '\n\n', and
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
                    # Make sure we dont' remove elements inside the markers.
                    # For a few Wikipedias (Chinese, Russian) the expansion of
                    # {{fact}} is marked as .noprint, which we otherwise want
                    # to remove.
                    inside_marker = any(
                        e.attrib.get('class') == CITATION_NEEDED_MARKER_CLASS
                        for e in element.iterancestors('span'))
                    if not inside_marker:
                        element.getparent().remove(element)

            if self._cfg.extract == 'snippet':
                # We climb up from each marker to the nearest antecessor element
                # that we can use as a snippet.
                snippet_roots = []
                for marker in tree.cssselect('.' + CITATION_NEEDED_MARKER_CLASS):
                    assert marker.attrib['class'] == CITATION_NEEDED_MARKER_CLASS
                    root = marker.getparent()
                    while root is not None and root.tag not in ('p', 'ol', 'ul'):
                        root = root.getparent()
                    if root is None:
                        continue

                    snippet_roots = [copy(root)]
                    if root.tag in ('ol', 'ul'):
                        snippet_roots = self._html_list_to_snippets(root)
            else:
                # Keep only a few whitelisted top-level elements within the
                # body. This is not great as any content within, say,
                # <blockquote> gets removed entirely, but it's good enough in
                # most cases.
                tree[0][:] = tree.cssselect('body > p, ol, ul')
                snippet_roots = [tree]

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
                for marker in markers_in_snippet:
                    marker.attrib['class'] = CITATION_NEEDED_MARKER_CLASS
                    self._remove_space_before_element(marker)

                length = len(sr.text_content().strip())
                if minlen < length < maxlen:
                    snippet = d(lxml.html.tostring(
                        sr, encoding = 'utf-8', method = 'html'))
                    snippets_in_section.add(snippet)

            sectitle = unicode(section.get(0).title.strip()) if i != 0 else ''
            snippets.append([sectitle, list(snippets_in_section)])
        return snippets

    def _html_list_to_snippets(self, list_element):
        """
        Given a <ol> or <ul> element containing a citation needed marker,
        in one of its <li>, transform it snippets by choosing a few of the
        <li> and getting rid of the others.
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
            sr = lxml.html.Element('div')
            sr.extend(preamble)
            sr.append(lxml.html.Element(list_element.tag))

            # Try to take one <li> before and one after the one we want, but
            # don't if they have nested lists in them, as that typically makes
            # the snippet too large.
            for before in li_with_marker.itersiblings('li', preceding = True):
                if not before.cssselect('ol, ul'):
                    sr[-1].append(copy(before))
                break
            sr[-1].append(copy(li_with_marker))
            for after in li_with_marker.itersiblings('li'):
                if not after.cssselect('ol, ul'):
                    sr[-1].append(copy(after))
                break
            snippet_roots.append(sr)
        return snippet_roots

    def _remove_space_before_element(self, element):
        if element.getprevious() is not None and element.getprevious().tail:
            element.getprevious().tail = element.getprevious().tail.rstrip()
        elif element.getparent() is not None and element.getparent().text:
            element.getparent().text = element.getparent().text.rstrip()

    def _strip_code(self, wikicode, normalize=True, collapse=True):
        '''A copy of mwparserfromhell's strip_code, using our methods.'''

        nodes = []
        for node in wikicode.nodes:
            if type(node) in self._strip_methods:
                stripped = self._strip_methods[type(node)](
                    node, normalize, collapse)
            else:
                stripped = node.__strip__(normalize, collapse)
            if stripped:
                nodes.append(unicode(stripped))

        if collapse:
            stripped = "".join(nodes).strip("\n")
            while "\n\n\n" in stripped:
                stripped = stripped.replace("\n\n\n", "\n\n")
            return stripped
        else:
	    return "".join(nodes)

    def _has_blacklisted_tag_or_template(self, wikicode):
        blacklisted_tag_or_template = itertools.chain(
            (tag.tag in self._cfg.tags_blacklist
                for tag in wikicode.filter_tags()),
            ((matches_any(tpl, self._cfg.templates_blacklist)
                for tpl in wikicode.filter_templates())
            if not self._cfg.html_snippet else iter([]))
        )
        return any(blacklisted_tag_or_template)

    # (s)anitize (p)arameters from a template
    def sp(self, params):
        if isinstance(params, mwparserfromhell.nodes.extras.Parameter):
            params = [params]
        sanitized = [unicode(self._strip_code(p.value)) for p in params]
        return sanitized[0] if len(sanitized) == 1 else sanitized

    def delegate_strip(self, obj, normalize, collapse):
        return obj.__strip__(normalize, collapse)

    def strip_template(self, template, normalize, collapse):
        '''Override to control how templates are stripped in the wikicode.

        The return value will be the template's replacement. The default
        implementation replaces the citation needed template with
        CITATION_NEEDED_MARKER, which you must take care to do when overriding.
        '''

        if self.is_citation_needed(template):
            repl = [CITATION_NEEDED_MARKER]
            # Keep the text in the template, but not other parameters like date
            repl = [self.sp(p) for p in template.params if not p.showkey] + repl
            return ''.join(repl)
        return template if self._cfg.html_snippet else ''

    def strip_tag(self, tag, normalize, collapse):
        '''Override to control how tags are stripped in the wikicode.

        The return value will be the tag's replacement. The default
        implementation replaces <ref> tags with REF_MARKER and handles a few
        other common tags, delegating other tags to mwparserfromhell.
        '''

        if tag.tag == 'ref':
            return REF_MARKER
        if not self._cfg.html_snippet:
            if tag.tag == 'dd':
                return ':'
            elif tag.tag == 'dt':
                return ''
            return self.delegate_strip(tag, normalize, collapse)
        else:
            # Strip contents, but it's generally fine to leave the tag itself
            if tag.contents:
                tag.contents = self._strip_code(tag.contents)
            return tag
        return ''

    def strip_wikilink(self, wikilink, normalize, collapse):
        '''Override to control how wikilinks are stripped in the wikicode.

        The return value will be the link's replacement. The default value
        will strip the wikilink entirely if its title has a prefix-match in
        config.wikilink_prefix_blacklist; otherwise, it will return the
        (stripped) text or title of the link.
        '''

        for prefix in self._cfg.wikilink_prefix_blacklist:
            if wikilink.title.startswith(prefix):
                return ''
        text = wikilink.text if wikilink.text else wikilink.title
        return self._strip_code(text)

    def strip_heading(self, heading, normalize, collapse):
        '''Override to control how headings are stripped in the wikicode.

        The default delegates to mwparserfromhell.nodes.Node.__strip__.
        '''

        return mwparserfromhell.nodes.Node.__strip__(
            heading, normalize, collapse)

    def is_citation_needed(self, template):
        '''Override to control which templates are considered Citation needed.

        The default implementation matches against
        config.citation_needed_templates.
        '''

        return template.name.lower().strip() in self._lowercase_cn_templates

    def extract(self, wikitext):
        return self.extract_html_snippets(wikitext)

    def extract_snippets(self, wikitext):
        """Extracts snippets lacking citations.

        This function looks for snippets of the article that are marked with any of
        the templates in `cfg.citation_needed_templates` from the `wikitext` passed
        as parameter.

        The return value is a list of lists of the form:
            [
                [<section1>, [<snippet1>, <snippet2>, ...]],
                [<section2>, [<snippet1>, ...]],
                ...
            ]
        """

        snippets = [] # [section, [snippets]]
        minlen, maxlen = self._cfg.snippet_min_size, self._cfg.snippet_max_size

        wikicode = self._fast_parse(wikitext)
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
                if self._has_blacklisted_tag_or_template(wikicode):
                    continue

                snippet = self._cleanup_snippet_text(self._strip_code(wikicode))
                if not self._cfg.html_snippet and '\n' in snippet:
                    # Lists cause more 'paragraphs' to be generated
                    paragraphs.extend(snippet.split('\n'))
                    continue

                if CITATION_NEEDED_MARKER not in snippet:
                    # marker may have been inside wiki markup
                    continue

                if not self._cfg.html_snippet:
                    usable_len = (
                        len(snippet) -
                        (len(CITATION_NEEDED_MARKER) *
                            snippet.count(CITATION_NEEDED_MARKER)) -
                        (len(REF_MARKER) *
                            snippet.count(REF_MARKER)))
                    if usable_len > maxlen or usable_len < minlen:
                        continue
                else:
                    # TODO Maybe batch all snippets and do a single API request?
                    length, snippet = self._to_html(snippet)
                    if not (minlen < length < maxlen):
                        continue
                    if CITATION_NEEDED_MARKER not in snippet:
                        # marker may have been removed in the HTML processing
                        continue
                secsnippets.append(snippet)
        return snippets

    def extract_sections(self, wikitext):
        """Extracts sections/subsections lacking citations.

        This function looks for sections of the article that are marked with any of
        the templates in `cfg.citation_needed_templates`.

        The return value is a list of lists of the form:
            [
                [<section1>, [<subsection1>, <subsection2>, ...]],
                [<section2>, [<subsection1>, ...]],
                ...
            ]
        """

        snippets = [] # [section, [snippets]]
        minlen, maxlen = self._cfg.snippet_min_size, self._cfg.snippet_max_size
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
                if matches_any(tpl, self._cfg.citation_needed_templates):
                    break
            else:
                # This section doesn't need references, move on to the next one
                continue

            if self._has_blacklisted_tag_or_template(section):
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
                self._strip_code(mwparserfromhell.wikicode.Wikicode(nodes)))

            # skip the templates that remained at the beginning and end
            empty_or_template = (lambda node:
                node == '' or
                isinstance(node, mwparserfromhell.nodes.template.Template) or
                re.match('^\n+$', e(node)))
            nodes = list(itertools.dropwhile(empty_or_template, wikicode.nodes))
            wikicode.nodes = reversed(list(
                itertools.dropwhile(empty_or_template, nodes[::-1])))
            snippet = self._cleanup_snippet_text(unicode(wikicode))

            # Chop off some paragraphs at the end until we're at a reasonable
            # size, since we don't actually display the whole thing in the UI
            # We'll often end up with just a section header here, so hopefully
            # it will be smaller than the minimum size when converted to HTML.
            # FIXME: Maybe this can be detected?
            snippet = '\n\n'.join(p.strip(' ') for p in snippet.split('\n\n')[:10])
            length, snippet = self._to_html(snippet)
            if length > minlen and length < maxlen:
                secsnippets.append(snippet)
        return snippets

    def _cleanup_snippet_text(self, snippet):
        snippet = re.sub(STRIP_REGEXP, r'\1', snippet).strip()
        snippet = re.sub(',\s+\)', ')', snippet)
        snippet = re.sub('\(\)\s', '', snippet)
        snippet = re.sub('\[\]\s', '', snippet)
        return snippet

    def _cleanup_snippet_html(self, html):
        tree = lxml.html.parse(
            StringIO.StringIO(e(html)),
            parser = lxml.html.HTMLParser(
                encoding = 'utf-8', remove_comments = True)).getroot()
        if tree is None:
            # TODO Log/investigate these
            return 0, ''

        # Links are always relative so they end up broken in the UI. We could make
        # them absolute, but let's just remove them (by replacing with <span>) since
        # we don't actually need them.
        for a in tree.findall('.//a'):
            a.tag = 'span'

        for css_selector in self._html_css_selectors_to_strip:
            for element in css_selector(tree):
                element.getparent().remove(element)

        # lxml wraps the HTML with proper <html><body> tags, so remove that
        newroot = tree.find('.//body')
        newroot.tag = 'div'

        return len(newroot.text_content()), d(lxml.html.tostring(
            newroot, encoding = 'utf-8', method = 'html'))

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

    def _to_html(self, snippet):
        if self._wikipedia is None:
            # Testing
            return len(snippet), snippet
        try:
            params = dict(text = snippet, **self._cfg.html_parse_parameters)
            result = self._wikipedia.parse(params)
            html = result['parse']['text']['*']
        except:
            return 0, ''
        return self._cleanup_snippet_html(html)

_log = Logger()

def create_snippet_parser(wikipedia, cfg):
    if os.path.dirname(__file__) not in sys.path:
        sys.path.append(os.path.dirname(__file__))
    try:
        localized_module = importlib.import_module(cfg.lang_code)
    except ImportError:
        _log.info('No snippet_parser for lang_code %s, using stub!' % cfg.lang_code)
        localized_module = importlib.import_module('stub')
    return localized_module.SnippetParser(wikipedia, cfg)
