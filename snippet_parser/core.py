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
import wikitools

import cStringIO as StringIO
import re
import importlib
import itertools
import lxml.html
import lxml.cssselect

REF_MARKER = 'ec5b89dc49c433a9521a139'
CITATION_NEEDED_MARKER = '7b94863f3091b449e6ab04d4'

STRIP_REGEXP = re.compile( # strip spaces before the markers
    '\s+(' + CITATION_NEEDED_MARKER + '|' + REF_MARKER + ')')

def matches_any(template, names):
    return any(template.name.matches(n) for n in names)

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

        self._citation_needed_templates = self._resolve_redirects_to_templates(
            self._cfg.citation_needed_templates)
        assert len(self._citation_needed_templates) > 0

        # Used for fast searching in the tokenize function
        self._lowercase_cn_templates = [
            t.lower() for t in self._citation_needed_templates]

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
            'action': 'query',
            'format': 'json',
            'prop': 'redirects',
            'titles': '|'.join(
                # The API resolves Template: to the relevant per-language prefix
                'Template:' + tplname
                for tplname in self._cfg.citation_needed_templates
            ),
            'rnamespace': 10,
        }
        request = wikitools.APIRequest(self._wikipedia, params)
        # We could fall back to just using self._cfg.citation_needed_templates
        # if the API request fails, but for now let's just crash
        for result in request.queryGen():
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
        elif str(tag.tag) in {'i', 'b', 'li', 'dt', 'dd'}:
            # strip the contents, but keep the tag itself
            tag.contents = self.delegate_strip(tag, normalize, collapse)
            return tag
        return ''

    def strip_wikilink(self, wikilink, normalize, collapse):
        '''Override to control how wikilinks are stripped in the wikicode.

        The return value will be the link's replacement. The default value
        will strip the wikilink entirely if its title has a prefix-match in
        config.wikilink_prefix_blacklist; otherwise, it will delegate to
        mwparserfromhell.
        '''

        for prefix in self._cfg.wikilink_prefix_blacklist:
            if wikilink.title.startswith(prefix):
                return ''
        return self.delegate_strip(wikilink, normalize, collapse)

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

        return any(
            template.name.matches(tpl)
            for tpl in self._citation_needed_templates)

    def extract(self, wikitext):
        if self._cfg.extract == 'snippet':
            return self.extract_snippets(wikitext)
        return self.extract_sections(wikitext)

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

                blacklisted_tag_or_template = itertools.chain(
                    (tag.tag in self._cfg.tags_blacklist
                        for tag in wikicode.filter_tags()),
                    (matches_any(tpl, self._cfg.templates_blacklist)
                        for tpl in wikicode.filter_templates()),
                )
                if any(blacklisted_tag_or_template):
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
                    snippet = self._to_html(snippet)
                    if not (minlen < len(snippet) < maxlen):
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
            snippet = self._to_html(snippet)
            if len(snippet) > minlen and len(snippet) < maxlen:
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
            return ''

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
        return d(lxml.html.tostring(
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
                any(t in t2.text.lower() for t in self._lowercase_cn_templates))
        try:
            return mwparserfromhell.parser.Builder().build(reduced_tokens)
        except mwparserfromhell.parser.ParserError:
            return None

    def _to_html(self, snippet):
        if self._wikipedia is None:
            # Testing
            return snippet

        params = {
            'action': 'parse',
            'format': 'json',
            'text': snippet,
        }
        request = wikitools.APIRequest(self._wikipedia, params)
        # FIXME Sometimes the request fails because the text is too long;
        # in that case, the API response is HTML, not JSON, which raises
        # an exception when wikitools tries to parse it.
        #
        # Normally this would cause wikitools to happily retry forever
        # (https://github.com/alexz-enwp/wikitools/blob/b71481796c350/wikitools/api.py#L304),
        # which is a bug, but due to our use of a custom opener, wikitools'
        # handling of the exception raises its own exception: the object returned
        # by our opener doesnt support seek().
        #
        # We use that interesting coincidence to catch the exception and move
        # on, bypassing wikitools' faulty retry, but this is obviously a terrible
        # "solution".
        try:
            html = request.query()['parse']['text']['*']
        except:
            return ''
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
