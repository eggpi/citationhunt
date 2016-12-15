#-*- encoding: utf-8 -*-
from __future__ import unicode_literals

from core import *

class SnippetParser(SnippetParserBase):
    def strip_template(self, template, normalize, collapse):
        if self.is_citation_needed(template):
            # we just suppress these for German
            return
        # TODO Also remove any templates under the German equivalent
        # of Category:Wikipedia_Maintenance_templates and/or
        # Category:Exclude_in_print?
        tplname = template.name.lower()
        if 'infobox' in tplname or 'taxobox' in tplname:
            return ''
        if template.name.matches('Überarbeiten'):
            return ''
        return template

    def strip_tag(self, tag, normalize, collapse):
        if tag.tag == 'ref':
            return REF_MARKER
        if str(tag.tag) in {'i', 'b', 'li', 'dt', 'dd'}:
            # strip the contents, but keep the tag itself
            tag.contents = self.delegate_strip(tag, normalize, collapse)
            return tag
        return ''

    def strip_heading(self, heading, normalize, collapse):
        if heading.level <= 2:
            return super(SnippetParser, self).strip_heading(
                heading, normalize, collapse)
        # Keep sub-headings, as the template we're looking for is often
        # applied right after 1 or 2-level headings, before a level 3 heading
        # However, "pre-render" them as bold so we don't have to deal with
        # their HTML representation (which includes links to edit the section).
        return "'''" + heading.title.strip() + "'''\n\n"
