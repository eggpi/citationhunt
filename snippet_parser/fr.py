#-*- encoding: utf-8 -*-
from __future__ import unicode_literals

from base import *

def handle_date(template):
    year = None
    if len(template.params) >= 3:
        try:
            year = int(sp(template.params[2]))
        except ValueError:
            pass
    if isinstance(year, int):
        # assume {{date|d|m|y|...}}
        return ' '.join(sp(template.params[:3]))
    elif template.params:
        # assume {{date|d m y|...}}
        return sp(template.params[0])
    return ''

def handle_s(template):
    if not template.params:
        return ''
    ret = sp(template.params[0]).upper()
    if len(template.params) == 2 and sp(template.params[1]) == 'er':
        ret += 'ᵉʳ'
    else:
        ret += 'ᵉ'
    ret += ' siècle'
    if template.name.matches('-s'):
        ret += ' av. J.-C'
    return ret

class SnippetParser(SnippetParserBase):
    def strip_template(self, template, normalize, collapse):
        repl = self.handle_common_templates(template, normalize, collapse)
        if repl is not None:
            return repl

        if template.name.matches('unité'):
            return ' '.join(sp(template.params[:2]))
        elif template.name.matches('date'):
            return handle_date(template)
        elif matches_any(template, ('s', '-s', 's-', 'siècle')):
            return handle_s(template)
        elif self.is_citation_needed(template):
            repl = [CITATION_NEEDED_MARKER]
            # Keep the text inside the template, but not other parameters
            # like date
            repl = [sp(p) for p in template.params if not p.showkey] + repl
            return ''.join(repl)
        return ''
