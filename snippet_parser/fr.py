#-*- encoding: utf-8 -*-
from __future__ import unicode_literals

from core import *

class SnippetParser(SnippetParserBase):
    def strip_template(self, template, normalize, collapse):
        if template.name.matches('unité'):
            return ' '.join(self.sp(self, template.params[:2]))
        elif template.name.matches('date'):
            return self.handle_date(template)
        elif matches_any(template, ('s', '-s', 's-', 'siècle')):
            return self.handle_s(template)
        elif template.name.matches('phonétique'):
            return self.handle_phonetique(template)
        elif template.name.matches('citation'):
            return self.handle_citation(template)
        elif template.name.matches('quand'):
            return self.handle_quand(template)
        elif template.name.matches('lesquelles'):
            return self.handle_lesquelles(template)
        elif template.name.matches('drapeau'):
            return self.handle_drapeau(template)
        return super(SnippetParser, self).strip_template(
                template, normalize, collapse)

    def handle_drapeau(self, template):
        return template.get(1)

    def handle_date(self, template):
        year = None
        if len(self, template.params) >= 3:
            try:
                year = int(self.sp(self, self, template.params[2]))
            except ValueError:
                pass
        if isinstance(year, int):
            # assume {{date|d|m|y|...}}
            return ' '.join(self.sp(self, self, template.params[:3]))
        elif template.params:
            # assume {{date|d m y|...}}
            return self.sp(self, self, template.params[0])
        return ''

    def handle_s(self, template):
        if not template.params:
            return ''
        ret = self.sp(template.params[0]).upper()
        if (len(template.params) == 2 and
            self.sp(template.params[1]) == 'er'):
            ret += 'ᵉʳ'
        else:
            ret += 'ᵉ'
        if template.name != 'siècle':
            ret += ' siècle'
        if template.name.matches('-s'):
            ret += ' av. J.-C'
        return ret

    def handle_phonetique(self, template):
        if not template.params:
            return ''
        return self.sp(template.params[0])

    def handle_citation(self, template):
        if template.params:
            return '« ' + self.sp(template.params[0]) + ' »'

    def handle_quand(self, template):
        return ''.join(self.sp(p) for p in template.params if not p.showkey)

    def handle_lesquelles(self, template):
        # quand and lesquelles are basically the same template
        return self.handle_quand(template)
