#-*- encoding: utf-8 -*-
from __future__ import unicode_literals

import chstrings

import os

global_config = dict(
    # Approximate maximum length for a snippet
    snippet_max_size = 500,

    # Approximate minimum length for a snippet
    snippet_min_size = 100,

    # If running on Tools labs, keep database dumps in this directory...
    archive_dir = os.path.join(os.path.expanduser('~'), 'ch_archives'),

    # ...and delete dumps that are older than this many days
    archive_duration_days = 90,

    flagged_off = [],

    # Profiling is enabled for individual languages
    profile = False,
)

# Most (all?) Wikipedias support these English settings in addition
# to the localized ones, so make sure to handle them!

EN_WIKILINK_PREFIX_BLACKLIST = [
    'File:',
    'Image:',
    'Media:'
]

EN_CITATION_NEEDED_TEMPLATES = [
    'Citation needed',
    'cn',
    'fact',
]

EN_TAGS_BLACKLIST = [
    'math',
]

EN_TEMPLATES_BLACKLIST = [
    'lang',
]

lang_code_to_config = dict(
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
        lead_section_policy_link = "https://en.wikipedia.org/wiki/Wikipedia:CITELEAD",
        # A human-readable title for the link above. This gets interpolated
        # into the localizable string 'lead_section_hint'
        lead_section_policy_link_title = "WP:CITELEAD",

        # The name of the category containing articles lacking
        # citations, without the 'Category:' prefix
        citation_needed_category = 'All_articles_with_unsourced_statements',

        # The names of templates that mark statements lacking
        # citations. The first letter is case-insensitive. When
        # adding a new language, this may help:
        # https://www.wikidata.org/wiki/Q5312535
        citation_needed_templates = EN_CITATION_NEEDED_TEMPLATES,

        # For consistency, we don't actually display each of the templates
        # listed in `citation_needed_templates` in the user interface; instead
        # we just replace them with one common name. For example, in the English
        # Wikipedia, we use the iconic [citation needed]. This should basically
        # match what the user would see on Wikipedia, minus the brackets.
        citation_needed_template_name = 'citation needed',

        # Wikilinks having these prefixes will be omitted
        # entirely from the output; others will get replaced
        # by their titles.
        wikilink_prefix_blacklist = EN_WIKILINK_PREFIX_BLACKLIST,

        # A set of tags that we know for sure we can't handle, so
        # snippets containing them will be dropped.
        tags_blacklist = EN_TAGS_BLACKLIST,

        # A set of templates that we know for sure we can't handle, so
        # snippets containing them will be dropped.
        templates_blacklist = EN_TAGS_BLACKLIST,

        # The name of the category for hidden categories. Categories
        # belonging to this category are typically used for maintenance
        # and should not show up on Citation Hunt.
        hidden_category = 'Hidden_categories',

        # Citation Hunt will ignore categories if their names match one
        # of these regular expressions.
        category_name_regexps_blacklist = [
            '^Articles',
            '^Pages ',
            ' stubs$',
            '.*[0-9]+.*',
        ],
    ),

    fr = dict(
        lang_name = 'Français',
        lang_dir = 'ltr',
        database = 'frwiki_p',
        wikipedia_domain = 'fr.wikipedia.org',
        citation_needed_category = 'Article_à_référence_nécessaire',
        beginners_link = 'https://fr.wikipedia.org/wiki/Aide:Pr%C3%A9sentez_vos_sources',
        beginners_link_title = 'Aide:Source',
        lead_section_policy_link = "https://fr.wikipedia.org/wiki/WP:INTRO",
        lead_section_policy_link_title = "WP:INTRO",

        # Looks like there are many other interesting templates:
        # https://fr.wikipedia.org/wiki/Aide:Référence_nécessaire
        citation_needed_templates = EN_CITATION_NEEDED_TEMPLATES + [
            'Inédit',
            'Référence nécessaire',
            'Référence souhaitée',
            'ref nec',
            'ref sou',
            'refnec',
            'refsou',
        ],
        citation_needed_template_name = 'réf. nécessaire',

        wikilink_prefix_blacklist = EN_WIKILINK_PREFIX_BLACKLIST + [
            'Fichier:',
        ],

        tags_blacklist = EN_TAGS_BLACKLIST,

        templates_blacklist = EN_TEMPLATES_BLACKLIST,

        hidden_category = 'Catégorie_cachée',

        category_name_regexps_blacklist = [
            '.*[0-9]+.*',
        ],

        profile = True,
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

        citation_needed_templates = EN_CITATION_NEEDED_TEMPLATES + [
            'Citazione necessaria',
            'Senza fonte',
        ],
        citation_needed_template_name = 'senza fonte',

        wikilink_prefix_blacklist = EN_WIKILINK_PREFIX_BLACKLIST,

        tags_blacklist = EN_TAGS_BLACKLIST,

        templates_blacklist = EN_TEMPLATES_BLACKLIST,

        hidden_category = 'Categorie_nascoste',

        category_name_regexps_blacklist = [
            '.*[0-9]+.*',
        ],

        profile = True,
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

        citation_needed_templates = EN_CITATION_NEEDED_TEMPLATES + [
            'fakt',
        ],
        citation_needed_template_name = 'potrzebne źródło',

        wikilink_prefix_blacklist = EN_WIKILINK_PREFIX_BLACKLIST,

        tags_blacklist = EN_TAGS_BLACKLIST,

        templates_blacklist = EN_TEMPLATES_BLACKLIST,

        hidden_category = 'Ukryte_kategorie',

        category_name_regexps_blacklist = [
            '.*[0-9]+.*',
        ],

        # Not fully translated
        flagged_off = ['404'],
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

        citation_needed_templates = EN_CITATION_NEEDED_TEMPLATES + [
            'Citació necessària',
            'CC',
            'CN',
        ],
        citation_needed_template_name = 'cal citació',

        wikilink_prefix_blacklist = EN_WIKILINK_PREFIX_BLACKLIST,

        tags_blacklist = EN_TAGS_BLACKLIST,

        templates_blacklist = EN_TEMPLATES_BLACKLIST,

        hidden_category = 'Categories_ocultes',

        category_name_regexps_blacklist = [
            '.*[0-9]+.*',
        ],

        # Not fully translated
        flagged_off = ['404'],

        profile = True,
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
        citation_needed_templates = EN_CITATION_NEEDED_TEMPLATES + ['דרוש מקור', ],
        citation_needed_template_name = 'דרוש מקור',
        wikilink_prefix_blacklist = EN_WIKILINK_PREFIX_BLACKLIST,
        tags_blacklist = EN_TAGS_BLACKLIST,
        templates_blacklist = EN_TAGS_BLACKLIST,
        hidden_category = 'קטגוריות_מוסתרות',
        category_name_regexps_blacklist = [
            '^ויקיפדיה',
            '^Pages ',
            ' stubs$',
            '.*[0-9]+.*',
        ],
    ),

    es = dict(
        lang_name = 'Español',
        lang_dir = 'ltr',
        database = 'eswiki_p',
        wikipedia_domain = 'es.wikipedia.org',

        beginners_link = 'https://es.wikipedia.org/wiki/Wikipedia:Referencias',
        beginners_link_title = 'Wikipedia:Referencias',
        lead_section_policy_link = 'https://es.wikipedia.org/wiki/Wikipedia:Secci%C3%B3n_introductoria#Referencias',
        lead_section_policy_link_title = 'Wikipedia:Sección introductoria',

        citation_needed_category = 'Wikipedia:Artículos_que_necesitan_referencias',
        citation_needed_templates = EN_CITATION_NEEDED_TEMPLATES + [
            'Añadir referencias',
            'Cita necesaria',
            'Citarequerida',
            'CN',
            'cr',
            'Citar',
            'Demostrar',
            'Falta cita',
            'Hechos',
            'Noref',
            'Pruébalo',
            'Sinref',
            'Sinreferencias',
            'Sin referencias',
        ],
        citation_needed_template_name = 'cita requerida',
        wikilink_prefix_blacklist = EN_WIKILINK_PREFIX_BLACKLIST,
        tags_blacklist = EN_TAGS_BLACKLIST,
        templates_blacklist = EN_TAGS_BLACKLIST,
        hidden_category = 'Wikipedia:Categorías_ocultas',
        category_name_regexps_blacklist = [
            '.*[0-9]+.*',
        ],

        profile = True,
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
        citation_needed_templates = EN_CITATION_NEEDED_TEMPLATES + [
            'তথ্যসূত্র প্রয়োজন',
            'তথ্যসূত্র যাচাই',
            'সত্যতা',
            'Check',
            'Vn',
            'Vs',
            'Verification needed',
            'Verifysource',
            'Verify source',
        ],
        citation_needed_template_name = 'তথ্যসূত্র প্রয়োজন|',
        wikilink_prefix_blacklist = EN_WIKILINK_PREFIX_BLACKLIST,
        tags_blacklist = EN_TAGS_BLACKLIST,
        templates_blacklist = EN_TAGS_BLACKLIST,
        hidden_category = 'লুকায়িত_বিষয়শ্রেণীসমূহ',
        category_name_regexps_blacklist = [
            '.*[0-9]+.*',
            '.*[০১২৩৪৫৬৭৮৯].*',
        ],

        snippet_min_size = 20,
    ),
)

# In py3: types.SimpleNamespace
class Config(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

def get_localized_config(lang_code = None):
    if lang_code is None:
        lang_code = os.getenv('CH_LANG')
    cfg = Config(lang_code = lang_code,
        **dict(global_config, **lang_code_to_config[lang_code]))
    cfg.strings = chstrings.get_localized_strings(cfg, lang_code)
    cfg.lang_code_to_config = lang_code_to_config
    return cfg
