#-*- encoding: utf-8 -*-
from __future__ import unicode_literals

from core import *

class SnippetParser(SnippetParserBase):
    def strip_template(self, template, normalize, collapse):
        if self.is_citation_needed(template):
            # we just suppress these for German
            return
        if template.name.matches('Überarbeiten'):
            return ''
        return template

    def strip_heading(self, heading, normalize, collapse):
        if heading.level <= 2:
            return super(SnippetParser, self).strip_heading(
                heading, normalize, collapse)
        # Keep sub-headings, as the template we're looking for is often
        # applied right after 1 or 2-level headings, before a level 3 heading.
        # We just make sure it will be a h3 by the time it comes back, so we
        # can apply styling to it later.
        return "<h3>" + heading.title.strip() + "</h3>\n\n"
