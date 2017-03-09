from core import *

class SnippetParser(SnippetParserBase):
    def strip_template(self, template, normalize, collapse):
        if self.is_citation_needed(template):
            repl = [
                # The text that needs citation might either appear in an
                # unnamed parameter, or in a parameter named '1'
                # (https://fr.wikipedia.org/wiki/Mod%C3%A8le:Refnec)
                self.sp(p) for p in template.params if p.showkey in (False, '1')
            ] + [CITATION_NEEDED_MARKER]
            return ''.join(repl)
        return super(SnippetParser, self).strip_template(
            template, normalize, collapse)
