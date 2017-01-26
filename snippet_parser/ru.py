#-*- encoding: utf-8 -*-

from core import *

class SnippetParser(SnippetParserBase):
    def strip_template(self, template, normalize, collapse):
        if self.is_citation_needed(template):
            # Some templates take optional day/month/year parameters, e.g.
            # {{нет АИ|23|01|2017}}, while others have a first parameter
            # that is actual text that we want to keep. Ideally we'd be able
            # to distinguish between them here using the template's name, but
            # due to redirects, this is not very straightforward. We resort to
            # identifying date parameters by parsing them as ints.
            text = ''
            if template.params:
                p = self.sp(template.params[0])
                try:
                    int(p)
                except ValueError:
                    text = p
            return text + CITATION_NEEDED_MARKER
        return super(SnippetParser, self).strip_template(
            template, normalize, collapse)
