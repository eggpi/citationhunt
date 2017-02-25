#-*- encoding: utf-8 -*-
from core import *

class SnippetParser(SnippetParserBase):
    def strip_template(self, template, normalize, collapse):
        if template.name.matches('仮リンク'):
            return ''.join(self.sp(template.params[0]))
        elif self.is_citation_needed(template):
            return CITATION_NEEDED_MARKER
        return ''
