from core import *

class SnippetParser(SnippetParserBase):
    def strip_template(self, template, normalize, collapse):
        if self.is_citation_needed(template):
            # These templates often contain other information
            # (date/justification), so we drop it all here
            return CITATION_NEEDED_MARKER
        return ''
