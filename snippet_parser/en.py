import base

class SnippetParser(base.SnippetParserBase):
    def strip_template(self, template, normalize, collapse):
        repl = self.handle_common_templates(template, normalize, collapse)
        if repl is not None:
            return repl

        if template.name.matches('convert'):
            return ' '.join(map(unicode, template.params[:2]))
        elif self.is_citation_needed(template):
            return base.CITATION_NEEDED_MARKER
        return ''
