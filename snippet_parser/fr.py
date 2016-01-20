#-*- encoding: utf-8 -*-

import base

class SnippetParser(base.SnippetParserBase):
    def strip_template(self, template, normalize, collapse):
        if template.name.matches('unité'):
            return ' '.join(map(unicode, template.params[:2]))
        elif self.is_citation_needed(template):
            repl = [base.CITATION_NEEDED_MARKER]
            if template.params:
                repl = [template.params[0].value.strip_code()] + repl
            return ''.join(repl)
        return ''
