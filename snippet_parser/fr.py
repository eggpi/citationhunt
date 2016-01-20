#-*- encoding: utf-8 -*-

import base

def handle_date(template):
    year = None
    if len(template.params) >= 3:
        try:
            year = int(unicode(template.params[2]))
        except ValueError:
            pass
    if isinstance(year, int):
        # assume {{date|d|m|y|...}}
        return ' '.join(map(unicode, template.params[:3]))
    else:
        # assume {{date|d m y|...}}
        return unicode(template.params[0])

def handle_s(template):
    ret = template.params[0]
    if len(template.params) == 2:
        ret += template.params[1]
    if template.name.matches('-s'):
        ret += ' av. J.-C'
    return ret

class SnippetParser(base.SnippetParserBase):
    def strip_template(self, template, normalize, collapse):
        if template.name.matches('unité'):
            return ' '.join(map(unicode, template.params[:2]))
        elif template.name.matches('date'):
            return handle_date(template)
        elif template.name.matches('s') or template.name.matches('-s'):
            return handle_s(template)
        elif self.is_citation_needed(template):
            repl = [base.CITATION_NEEDED_MARKER]
            if template.params:
                repl = [template.params[0].value.strip_code()] + repl
            return ''.join(repl)
        return ''
