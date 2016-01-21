#-*- encoding: utf-8 -*-
from __future__ import unicode_literals

import base

def matches_any(template, names):
    return any(template.name.matches(n) for n in names)

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
    elif template.params:
        # assume {{date|d m y|...}}
        return unicode(template.params[0])
    return ''

def handle_s(template):
    if not template.params:
        return ''
    ret = unicode(template.params[0])
    if len(template.params) == 2 and unicode(template(params[1])) == 'er':
        ret += 'ᵉʳ'
    else:
        ret += 'ᵉ'
    ret += ' siècle'
    if template.name.matches('-s'):
        ret += ' av. J.-C'
    return ret

class SnippetParser(base.SnippetParserBase):
    def strip_template(self, template, normalize, collapse):
        repl = self.handle_common_templates(template, normalize, collapse)
        if repl is not None:
            return repl

        if template.name.matches('unité'):
            return ' '.join(map(unicode, template.params[:2]))
        elif template.name.matches('date'):
            return handle_date(template)
        elif matches_any(template, ('s', '-s', 's-')):
            return handle_s(template)
        elif self.is_citation_needed(template):
            repl = [base.CITATION_NEEDED_MARKER]
            if template.params:
                repl = [template.params[0].value.strip_code()] + repl
            return ''.join(repl)
        return ''
