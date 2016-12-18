#-*- encoding: utf-8 -*-
from __future__ import unicode_literals

from core import *

class SnippetParser(SnippetParserBase):
    def strip_template(self, template, normalize, collapse):
        if template.name.matches('bandiera'):
            return self.handle_bandiera(template)
        elif template.name.matches('citazione'):
            return self.handle_citazione(template)
        return super(SnippetParser, self).strip_template(
                template, normalize, collapse)

    def handle_bandiera(template):
        return template.get(1)

    def handle_citazione(template):
        if template.params:
            return '« ' + self.sp(template.params[0]) + ' »'
