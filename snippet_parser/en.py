from core import *

class SnippetParser(SnippetParserBase):
    def strip_template(self, template, normalize, collapse):
        if template.name.matches('convert'):
            return ' '.join(self.sp(template.params[:2]))
        elif template.name.matches('flag'):
            return self.handle_flag(template)
        elif self.is_citation_needed(template):
            return CITATION_NEEDED_MARKER
        return ''

    def handle_flag(self, template):
        if template.has('name'):
            return self.sp(template.get('name'))
        return self.sp(template.params[0])
