#-*- encoding: utf-8 -*-
from __future__ import unicode_literals

import chstrings

import os

global_config = dict(
    # Approximate maximum length for a snippet
    snippet_max_size = 420,

    # Approximate minimum length for a snippet
    snippet_min_size = 100,

    flagged_off = ['404']
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

        # The maximum number of categories to use, excluding pinned categories
        max_categories = 3500,
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

        max_categories = 1000,
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

        max_categories = 1000,
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

        max_categories = 1000,
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

        max_categories = 100,
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
