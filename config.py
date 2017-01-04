#-*- encoding: utf-8 -*-
from __future__ import unicode_literals

import chstrings

import os

# The configuration for a language is a set of key/value pairs, where the
# values may be True/False, strings or lists of strings. It is computed by
# inheriting from the global config, base config, and language-specific
# config below, in that order.
# When inheriting, for simple string or True/False keys, the "inheritor's"
# value overrides the base value, and for list values, the base and inheritor
# lists are merged. There is currently no way to completely override a base list
# value.

# Configuration keys that don't correspond to user-visible or snippet parsing
# behavior. Boring stuff.
_GLOBAL_CONFIG = dict(
    # If running on Tools labs, keep database dumps in this directory...
    archive_dir = os.path.join(os.path.expanduser('~'), 'ch_archives'),

    # ...and delete dumps that are older than this many days
    archive_duration_days = 90,

    # Where to put various logs
    log_dir = os.path.join(os.path.expanduser('~'), 'ch_logs'),

    flagged_off = [],

    profile = True,

    stats_max_age_days = 90,
)

# A base configuration that all languages "inherit" from.
_BASE_LANG_CONFIG = dict(
    # Approximate maximum length for a snippet
    snippet_max_size = 500,

    # Approximate minimum length for a snippet
    snippet_min_size = 100,

    # Whether or not snippets should be converted to HTML using the
    # Wikipedia API before storing them in the database
    html_snippet = False,

    # When html_snippet is True, the elements identified by these CSS selectors
    # are removed from the HTML returned by the Wikipedia API
    html_css_selectors_to_strip = [
        '.hatnote',
        '.noexcerpt',
        '.references',
        'table',
    ],

    # What to extract for each citation needed template found in the wikitext,
    # either 'snippet' or 'section'
    extract = 'snippet',

    # Most (all?) Wikipedias support the English settings below in addition
    # to the localized ones, so make sure to handle them!

    # Wikilinks having these prefixes will be omitted entirely from the output;
    # others will get replaced by their titles.
    wikilink_prefix_blacklist = [
        'File:',
        'Image:',
        'Media:'
    ],

    # The names of templates that mark statements lacking citations. The
    # first letter is case-insensitive. When adding a new language, this
    # may help: https://www.wikidata.org/wiki/Q5312535
    # Other templates that redirect to any of these templates are also
    # processed automatically, so there's no need to list them here.
    citation_needed_templates = [
        'Citation needed',
    ],

    # A set of tags that we know for sure we can't handle, so  snippets
    # containing them will be dropped.
    tags_blacklist = [
        'math',
    ],

    # A set of templates that we know for sure we can't handle, so
    # snippets containing them will be dropped.
    templates_blacklist = [
        'lang',
    ],

    # Citation Hunt will ignore categories if their names match one
    # of these regular expressions.
    category_name_regexps_blacklist = [
        '^Articles',
        '^Pages ',
        ' stubs$',
        '.*[0-9]+.*',
    ],
)

# Language-specific config, inheriting from the base config above.
_LANG_CODE_TO_CONFIG = dict(
    en = dict(
        # A friendly name for the language
        lang_name = 'English',
        # The direction of the language, either ltr or rtl
        lang_dir = 'ltr',
        # The database to use on Tools Labs
        database = 'enwiki_p',
        # The domain for Wikipedia in this language
        wikipedia_domain = 'en.wikipedia.org',

        # A link to an introductory article about adding citations
        beginners_link = 'https://en.wikipedia.org/wiki/Help:Introduction_to_referencing_with_VisualEditor/1',
        # A human-readable title for the article specified above. This gets
        # interpolated into the localizable string 'beginners_hint'
        beginners_link_title = 'Introduction to referencing with VisualEditor',

        # Some Wikipedias have specific policies for adding citations to the
        # lead section of an article. This should be a link to that policy.
        lead_section_policy_link = 'https://en.wikipedia.org/wiki/Wikipedia:CITELEAD',
        # A human-readable title for the link above. This gets interpolated
        # into the localizable string 'lead_section_hint'
        lead_section_policy_link_title = 'WP:CITELEAD',

        # The name of the category containing articles lacking
        # citations, without the 'Category:' prefix and with underscores
        # instead of spaces.
        citation_needed_category = 'All_articles_with_unsourced_statements',

        # For consistency, we don't actually display each of the templates
        # listed in `citation_needed_templates` in the user interface; instead
        # we just replace them with one common name. For example, in the English
        # Wikipedia, we use the iconic [citation needed]. This should basically
        # match what the user would see on Wikipedia, minus the brackets.
        citation_needed_template_name = 'citation needed',

        # The name of the category for hidden categories, without the
        # 'Category:' prefix and with underscores instead of spaces.
        # Categories belonging to this category are typically used for
        # maintenance and will not show up on Citation Hunt.
        hidden_category = 'Hidden_categories',
    ),

    fr = dict(
        lang_name = 'Français',
        lang_dir = 'ltr',
        database = 'frwiki_p',
        wikipedia_domain = 'fr.wikipedia.org',
        citation_needed_category = 'Article_à_référence_nécessaire',
        beginners_link = 'https://fr.wikipedia.org/wiki/Aide:Pr%C3%A9sentez_vos_sources',
        beginners_link_title = 'Aide:Source',
        lead_section_policy_link = 'https://fr.wikipedia.org/wiki/WP:INTRO',
        lead_section_policy_link_title = 'WP:INTRO',

        # Looks like there are many other interesting templates:
        # https://fr.wikipedia.org/wiki/Aide:Référence_nécessaire
        citation_needed_templates = [
            'Inédit',
            'Référence nécessaire',
            'Référence souhaitée',
        ],
        citation_needed_template_name = 'réf. nécessaire',

        wikilink_prefix_blacklist = [
            'Fichier:',
        ],

        hidden_category = 'Catégorie_cachée',
    ),

    it = dict(
        lang_name = 'Italiano',
        lang_dir = 'ltr',
        database = 'itwiki_p',
        wikipedia_domain = 'it.wikipedia.org',
        citation_needed_category = 'Informazioni_senza_fonte',
        beginners_link = 'https://it.wikipedia.org/wiki/Aiuto:Uso_delle_fonti',
        beginners_link_title = 'Aiuto:Uso_delle_fonti',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_templates = [
            'Citazione necessaria',
            'Senza fonte',
        ],
        citation_needed_template_name = 'senza fonte',

        hidden_category = 'Categorie_nascoste',
    ),

    pl = dict(
        lang_name = 'Polski',
        lang_dir = 'ltr',
        database = 'plwiki_p',
        wikipedia_domain = 'pl.wikipedia.org',
        citation_needed_category = 'Artykuły_wymagające_uzupełnienia_źródeł',
        beginners_link = 'https://pl.wikipedia.org/wiki/Pomoc:Przypisy',
        beginners_link_title = 'Pomoc:Przypisy',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_templates = [
            'fakt',
        ],
        citation_needed_template_name = 'potrzebne źródło',

        hidden_category = 'Ukryte_kategorie',
    ),

    ca = dict(
        lang_name = 'Català',
        lang_dir = 'ltr',
        database = 'cawiki_p',
        wikipedia_domain = 'ca.wikipedia.org',
        citation_needed_category = 'Articles_amb_referències_puntuals_demanades',
        beginners_link = 'https://ca.wikipedia.org/wiki/Viquip%C3%A8dia:Guia_per_referenciar',
        beginners_link_title = 'Viquipèdia:Guia per referenciar',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_templates = [
            'Citació necessària',
            'CC',
            'CN',
        ],
        citation_needed_template_name = 'cal citació',

        hidden_category = 'Categories_ocultes',

        # Not fully translated
        flagged_off = ['404'],
    ),

    he = dict(
        lang_name = 'עברית',
        lang_dir = 'rtl',
        database = 'hewiki_p',
        wikipedia_domain = 'he.wikipedia.org',

        beginners_link = 'https://he.wikipedia.org/wiki/%D7%A2%D7%96%D7%A8%D7%94:%D7%94%D7%A2%D7%A8%D7%AA_%D7%A9%D7%95%D7%9C%D7%99%D7%99%D7%9D',
        beginners_link_title = 'עזרה:הערת_שוליים',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_category = 'ויקיפדיה:_ערכים_הדורשים_מקורות',
        citation_needed_templates = ['דרוש מקור'],
        citation_needed_template_name = 'דרוש מקור',
        hidden_category = 'קטגוריות_מוסתרות',
        category_name_regexps_blacklist = [
            '^ויקיפדיה',
        ],
    ),

    es = dict(
        lang_name = 'Español',
        lang_dir = 'ltr',
        database = 'eswiki_p',
        wikipedia_domain = 'es.wikipedia.org',

        beginners_link = 'https://es.wikipedia.org/wiki/Ayuda:Introducci%C3%B3n_a_las_referencias_con_Editor_Visual/1',
        beginners_link_title = 'Introducción a las referencias con Editor Visual',
        lead_section_policy_link = 'https://es.wikipedia.org/wiki/Wikipedia:Secci%C3%B3n_introductoria#Referencias',
        lead_section_policy_link_title = 'Wikipedia:Sección introductoria',

        citation_needed_category = 'Wikipedia:Artículos_con_pasajes_que_requieren_referencias',
        citation_needed_templates = [
            'Añadir referencias',
            'Cita requerida'
        ],
        citation_needed_template_name = 'cita requerida',
        hidden_category = 'Wikipedia:Categorías_ocultas',
    ),

    bn = dict(
        lang_name = 'বাংলা',
        lang_dir = 'ltr',
        database = 'bnwiki_p',
        wikipedia_domain = 'bn.wikipedia.org',

        beginners_link =
        'https://bn.wikipedia.org/wiki/%E0%A6%89%E0%A6%87%E0%A6%95%E0%A6%BF%E0%A6%AA%E0%A6%BF%E0%A6%A1%E0%A6%BF%E0%A6%AF%E0%A6%BC%E0%A6%BE:%E0%A6%89%E0%A7%8E%E0%A6%B8%E0%A6%A8%E0%A6%BF%E0%A6%B0%E0%A7%8D%E0%A6%A6%E0%A7%87%E0%A6%B6',
        beginners_link_title = 'উইকিপিডিয়া:উৎসনির্দেশ',
        lead_section_policy_link =
        'https://bn.wikipedia.org/wiki/%E0%A6%89%E0%A6%87%E0%A6%95%E0%A6%BF%E0%A6%AA%E0%A6%BF%E0%A6%A1%E0%A6%BF%E0%A6%AF%E0%A6%BC%E0%A6%BE:%E0%A6%AD%E0%A7%82%E0%A6%AE%E0%A6%BF%E0%A6%95%E0%A6%BE%E0%A6%82%E0%A6%B6_%E0%A6%A8%E0%A7%80%E0%A6%A4%E0%A6%BF%E0%A6%AE%E0%A6%BE%E0%A6%B2%E0%A6%BE#.E0.A6.A4.E0.A6.A5.E0.A7.8D.E0.A6.AF.E0.A6.B8.E0.A7.82.E0.A6.A4.E0.A7.8D.E0.A6.B0',
        lead_section_policy_link_title = 'WP:CITELEAD',

        citation_needed_category = 'উৎসবিহীন_তথ্যসহ_সকল_নিবন্ধ',
        # Some of these are not exactly [citation needed] but bnwiki is quite
        # small, so they help.
        citation_needed_templates = [
            'তথ্যসূত্র প্রয়োজন',
            'তথ্যসূত্র যাচাই',
            'সত্যতা',
            'Check',
            'Verification needed',
            'Verify source',
        ],
        citation_needed_template_name = 'তথ্যসূত্র প্রয়োজন|',
        hidden_category = 'লুকায়িত_বিষয়শ্রেণীসমূহ',
        category_name_regexps_blacklist = [
            '.*[০১২৩৪৫৬৭৮৯].*',
        ],

        snippet_min_size = 20,
    ),

    cs = dict(
        lang_name = 'Čeština',
        lang_dir = 'ltr',
        database = 'cswiki_p',
        wikipedia_domain = 'cs.wikipedia.org',

        beginners_link = 'https://cs.wikipedia.org/wiki/Wikipedie:Pr%C5%AFvodce/Vkl%C3%A1d%C3%A1n%C3%AD_citac%C3%AD',
        beginners_link_title = 'Wikipedie:Průvodce/Vkládání citací',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_category = 'Údržba:Články_obsahující_nedoložená_tvrzení',
        citation_needed_templates = [
            'Není ve zdroji',
            'Doplňte zdroj',
            'Fakt/dne',
        ],
        citation_needed_template_name = 'zdroj?',
        hidden_category = 'Wikipedie:Skryté_kategorie',
    ),

    sv = dict(
        lang_name = 'Svenska',
        lang_dir = 'ltr',
        database = 'svwiki_p',
        wikipedia_domain = 'sv.wikipedia.org',

        beginners_link = 'https://sv.wikipedia.org/wiki/Wikipedia:K%C3%A4llh%C3%A4nvisningar',
        beginners_link_title = 'Wikipedia:Källhänvisningar',
        lead_section_policy_link = 'https://sv.wikipedia.org/wiki/Wikipedia:K%C3%A4llh%C3%A4nvisningar#N.C3.A4r_beh.C3.B6ver_man_inte_ange_en_k.C3.A4lla.3F',
        lead_section_policy_link_title = 'Wikipedia:Källhänvisningar',

        citation_needed_category = 'Alla_artiklar_som_behöver_enstaka_källor',
        citation_needed_templates = [
            'kb',
            'Källa behövs',
            'Referens behövs',
        ],
        citation_needed_template_name = 'källa behövs',
        hidden_category = 'Dolda_kategorier',
    ),

    nb = dict(
        lang_name = 'Norsk (bokmål)',
        lang_dir = 'ltr',
        database = 'nowiki_p',
        wikipedia_domain = 'no.wikipedia.org',

        beginners_link = 'https://no.wikipedia.org/wiki/Wikipedia:Bruk_av_kilder',
        beginners_link_title = 'Wikipedia:Bruk av kilder',
        lead_section_policy_link = 'https://no.wikipedia.org/wiki/Wikipedia:Bruk_av_kilder#Hvorfor_siterer_vi_kilder',
        lead_section_policy_link_title = 'Wikipedia:Bruk_av_kilder',

        citation_needed_category = 'Artikler_som_trenger_referanser',
        citation_needed_templates = [
            'Trenger referanse',
            'Referanse',
        ],
        citation_needed_template_name = 'trenger referanse',
        hidden_category = 'Skjulte_kategorier',
    ),

    nn = dict(
        lang_name = 'Norsk (nynorsk)',
        lang_dir = 'ltr',
        database = 'nnwiki_p',
        wikipedia_domain = 'nn.wikipedia.org',

        beginners_link = 'https://nn.wikipedia.org/wiki/Wikipedia:Kjelder',
        beginners_link_title = 'Wikipedia:Kjelder',
        lead_section_policy_link = 'https://nn.wikipedia.org/wiki/Wikipedia:Kjelder#Korleis_oppgje_kjelder',
        lead_section_policy_link_title = 'Wikipedia:Kjelder',

        citation_needed_category = 'Artiklar_som_manglar_kjelder',
        citation_needed_templates = [
            'Treng kjelde',
        ],
        citation_needed_template_name = 'treng kjelde',
        hidden_category = 'Gøymde_kategoriar',
    ),

    fi = dict(
        lang_name = 'Suomi',
        lang_dir = 'ltr',
        database = 'fiwiki_p',
        wikipedia_domain = 'fi.wikipedia.org',

        beginners_link = 'https://fi.wikipedia.org/wiki/Ohje:L%C3%A4hteen_lis%C3%A4%C3%A4minen_visuaalisella_muokkaimella/1',
        beginners_link_title = 'Lähteen lisääminen visuaalisella muokkaimella',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_category = 'Puutteelliset_lähdemerkinnät',
        citation_needed_templates = [
            'Lähde',
            'Lähde tarkemmin',
            'Kenen mukaan',
        ],
        citation_needed_template_name = 'lähde?',
        hidden_category = 'Piilotetut_luokat',
    ),

    de = dict(
        lang_name = 'Deutsch',
        lang_dir = 'ltr',
        database = 'dewiki_p',
        wikipedia_domain = 'de.wikipedia.org',

        beginners_link = 'https://de.wikipedia.org/wiki/Wikipedia:Literatur',
        beginners_link_title = 'Wikipedia:Literatur',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        # For German, we just display the lead section of the article, so
        # some of these keys don't apply
        citation_needed_category = 'Wikipedia:Belege_fehlen',
        citation_needed_templates = [
            'Belege fehlen',
        ],
        citation_needed_template_name = '',
        wikilink_prefix_blacklist = [
            'Datei:',
            'Kategorie:',
            'Bild:',
        ],
        tags_blacklist = [],
        templates_blacklist = [],
        hidden_category = 'Kategorie:Versteckt',

        html_snippet = True,
        html_css_selectors_to_strip = [
            '.noprint',
        ],

        extract = 'section',

        # We use big chunks of sections for German, and convert them to
        # HTML. The min/max sizes apply to the final HTML.
        snippet_min_size = 200,
        snippet_max_size = 30000,
    ),

    el = dict(
        lang_name = 'Ελληνικά',
        lang_dir = 'ltr',
        database = 'elwiki_p',
        wikipedia_domain = 'el.wikipedia.org',

        beginners_link = 'https://el.wikipedia.org/wiki/Βοήθεια:Προσθήκη_παραπομπών_με_τον_VisualEditor',
        beginners_link_title = 'Προσθήκη παραπομπών με τον VisualEditor',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_category = 'Λήμματα_που_χρειάζονται_παραπομπές_με_επισήμανση',
        citation_needed_templates = [
            'Εκκρεμεί παραπομπή',
        ],
        citation_needed_template_name = 'Εκκρεμεί παραπομπή',
        hidden_category = 'Κρυμμένες_κατηγορίες',
        snippet_max_size = 700,
    ),

    lv = dict(
        lang_name = 'Latviešu',
        lang_dir = 'ltr',
        database = 'lvwiki_p',
        wikipedia_domain = 'lv.wikipedia.org',

        beginners_link = 'https://lv.wikipedia.org/wiki/Pal%C4%ABdz%C4%ABba:Atsauces',
        beginners_link_title = 'Palīdzība:Atsauces',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_category = 'Raksti,_kuru_apgalvojumiem_nepieciešamas_atsauces',
        citation_needed_templates = [
            'Nepieciešama atsauce',
        ],
        wikilink_prefix_blacklist = [
            'Attēls',
        ],
        citation_needed_template_name = 'nepieciešama atsauce',
        hidden_category = 'Slēptās_kategorijas',
        html_snippet = True,
        snippet_max_size = 5000,
    ),
)

# In py3: types.SimpleNamespace
class Config(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

def _inherit(base, child):
    ret = dict(base)  # shallow copy
    for k, v in child.iteritems():
        if k in ret and isinstance(v, list):
            ret[k] = ret[k] + v  # copy
        else:
            ret[k] = v
    return ret

LANG_CODES_TO_LANG_NAMES = {
    lang_code: _LANG_CODE_TO_CONFIG[lang_code]['lang_name']
    for lang_code in _LANG_CODE_TO_CONFIG
}

def get_global_config():
    return Config(**_GLOBAL_CONFIG)

def get_localized_config(lang_code = None):
    if lang_code is None:
        lang_code = os.getenv('CH_LANG')
    lang_config = _LANG_CODE_TO_CONFIG[lang_code]
    cfg = Config(lang_code = lang_code, **reduce(
        _inherit, [_GLOBAL_CONFIG, _BASE_LANG_CONFIG, lang_config]))
    cfg.strings = chstrings.get_localized_strings(cfg, lang_code)
    cfg.lang_codes_to_lang_names = LANG_CODES_TO_LANG_NAMES
    return cfg
