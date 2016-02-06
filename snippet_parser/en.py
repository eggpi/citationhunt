from base import *

class SnippetParser(SnippetParserBase):
    def strip_template(self, template, normalize, collapse):
        if template.name.matches('convert'):
            return ' '.join(sp(template.params[:2]))
        elif self.is_citation_needed(template):
            return CITATION_NEEDED_MARKER
        return ''
