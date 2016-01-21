from base import *

class SnippetParser(SnippetParserBase):
    def strip_template(self, template, normalize, collapse):
        repl = self.handle_common_templates(template, normalize, collapse)
        if repl is not None:
            return repl

        if template.name.matches('convert'):
            return ' '.join(sp(template.params[:2]))
        elif self.is_citation_needed(template):
            return CITATION_NEEDED_MARKER
        return ''
