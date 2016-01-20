import base

class SnippetParser(base.SnippetParserBase):
    def strip_template(self, template, normalize, collapse):
        if template.name.matches('convert'):
            return ' '.join(map(unicode, template.params[:2]))
        elif self.is_citation_needed(template):
            return base.CITATION_NEEDED_MARKER
        return ''
