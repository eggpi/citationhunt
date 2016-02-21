from base import *

def handle_flag(template):
    if template.has('name'):
        return sp(template.get('name'))
    return sp(template.params[0])

class SnippetParser(SnippetParserBase):
    def strip_template(self, template, normalize, collapse):
        if template.name.matches('convert'):
            return ' '.join(sp(template.params[:2]))
        elif template.name.matches('flag'):
            return handle_flag(template)
        elif self.is_citation_needed(template):
            return CITATION_NEEDED_MARKER
        return ''
