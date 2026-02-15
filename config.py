#-*- encoding: utf-8 -*-

import datetime
import os
import types
from functools import reduce

# The configuration for a language is a set of key/value pairs, where the
# values may be True/False, strings or lists/dicts of strings. It is computed
# by inheriting from the global config, base config, and language-specific
# config below, in that order.
# When inheriting, for simple string or True/False keys, the "inheritor's"
# value overrides the base value, and for list/dict values, the base and
# inheritor lists are merged. There is currently no way to completely override
# a base list/dict value.

# Configuration keys that don't correspond to user-visible or snippet parsing
# behavior. Boring stuff.
_GLOBAL_CONFIG = dict(
    # If running on Tools labs, keep database dumps in this directory...
    archive_dir = os.path.join(os.path.expanduser('~'), 'ch_archives'),

    # ...and delete dumps that are older than this many days
    archive_duration_days = 90,

    # Where to put various logs
    log_dir = os.path.join(os.path.expanduser('~'), 'ch_logs'),

    # The lang_tag to use for untranslated strings.
    fallback_lang_tag = 'en',

    flagged_off = [],

    profile = False,

    stats_max_age_days = 90,

    user_agent = 'citationhunt (https://tools.wmflabs.org/citationhunt)',

    petscan_url = 'https://petscan.wmflabs.org',

    petscan_timeout_s = 180,

    petscan_depth = 10,

    pagepile_url = 'https://pagepile.toolforge.org',

    pagepile_timeout_s = 60,

    # The maximum number of articles to import into an intersection.
    intersection_max_size = 8192,

    # How long before an intersection is deleted from the database.
    intersection_expiration_days = 30,

    api = types.SimpleNamespace(
        # Maximum number of snippets to return from our API methods.
        max_returned_snippets = 200,
    ),
)

# A base configuration that all languages "inherit" from.
_BASE_LANG_CONFIG = dict(
    # Approximate maximum length for a snippet
    snippet_max_size = 800,

    # Approximate minimum length for a snippet
    snippet_min_size = 100,

    # Don't publish an update to the database if it has too little data
    min_snippets_sanity_check = 100,
    min_articles_sanity_check = 100,

    # The elements identified by these CSS selectors are removed from the HTML
    # returned by the Wikipedia API.
    html_css_selectors_to_strip = [
        '.hatnote',
        '.noexcerpt',
        '.noprint',
        '.notice',
        '.references',
        '.gallery',
        'br',
        'gallery',
        'table',
    ],

    # Parameters to pass to the Wikipedia API's parse method when converting
    # snippets to HTML, in addition to the snippet itself.
    html_parse_parameters = {
        'disabletoc': 'true',
        'disableeditsection': 'true',
        'wrapoutputclass': '',
    },

    # What to extract for each citation needed template found in the wikitext,
    # either 'snippet' or 'section'
    extract = 'snippet',

    # Most (all?) Wikipedias support the English settings below in addition
    # to the localized ones, so make sure to handle them!

    # The names of templates that mark statements lacking citations. The
    # first letter is case-insensitive. When adding a new language, this
    # may help: https://www.wikidata.org/wiki/Q5312535
    # Other templates that redirect to any of these templates are also
    # processed automatically, so there's no need to list them here.
    citation_needed_templates = [
        'Citation needed',
    ],

    # Citation Hunt will ignore categories if their names match one
    # of these regular expressions.
    category_name_regexps_blacklist = [
        '^Articles',
        '^Pages ',
        ' stubs$',
        '.*[0-9]+.*',
    ],

    # Locales that apply to this language config, to be matched against
    # the Accept-Language header. This is used for:
    #   - choosing which config to redirect the user to when they access /
    #   - choosing which strings to use in the UI when they access /<lang_code>
    # For the second case, the last value on this list is used as a fallback
    # if no match happens; if this is empty, the fallback is the language
    # code itself. Whatever the fallback is, it MUST match the name of some
    # file inside the chstrings/ directory.
    accept_language = [],

    # Snippets whose citation needed template is older than this get a notice
    # in the UI to nudge the user to delete the snippet. Set to None to disable.
    old_snippet_threshold = datetime.timedelta(weeks = 52 * 4)
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

        # A link to an introductory article about identifying reliable sources.
        # Optional.
        reliable_sources_link = 'https://en.wikipedia.org/wiki/Help:Introduction_to_referencing_with_VisualEditor/5',

        # Some Wikipedias have specific policies for adding citations to the
        # lead section of an article. This should be a link to that policy.
        lead_section_policy_link = 'https://en.wikipedia.org/wiki/Wikipedia:CITELEAD',
        # A human-readable title for the link above. This gets interpolated
        # into the localizable string 'lead_section_hint'
        lead_section_policy_link_title = 'WP:CITELEAD',

        # The name of the category for hidden categories, without the
        # 'Category:' prefix and with underscores instead of spaces.
        # Categories belonging to this category are typically used for
        # maintenance and will not show up on Citation Hunt.
        hidden_category = 'Hidden_categories',
    ),

    simple = dict(
        lang_name = 'Simple English',
        lang_dir = 'ltr',
        database = 'simplewiki_p',
        wikipedia_domain = 'simple.wikipedia.org',

        beginners_link = 'https://simple.wikipedia.org/wiki/Wikipedia:Citing_sources',
        beginners_link_title = 'Introduction to referencing / citing sources',

        reliable_sources_link = 'https://simple.wikipedia.org/wiki/Wikipedia:Reliable_sources',

        lead_section_policy_link = 'https://simple.wikipedia.org/wiki/Wikipedia:Lead_section',
        lead_section_policy_link_title = 'WP:LEAD',

        accept_language = ['en'],
        hidden_category = 'Hidden_categories',
    ),

    ar = dict(
        lang_name = 'العربية',
        lang_dir = 'rtl',
        database = 'arwiki_p',
        wikipedia_domain = 'ar.wikipedia.org',

        beginners_link = 'https://ar.wikipedia.org/wiki/%D9%88%D9%8A%D9%83%D9%8A%D8%A8%D9%8A%D8%AF%D9%8A%D8%A7:%D8%A7%D9%84%D8%A7%D8%B3%D8%AA%D8%B4%D9%87%D8%A7%D8%AF_%D8%A8%D9%85%D8%B5%D8%A7%D8%AF%D8%B1',
        beginners_link_title = 'ويكيبيديا:الاستشهاد بمصادر',

        reliable_sources_link = 'https://ar.wikipedia.org/wiki/%D9%88%D9%8A%D9%83%D9%8A%D8%A8%D9%8A%D8%AF%D9%8A%D8%A7:%D9%85%D8%B5%D8%A7%D8%AF%D8%B1_%D9%85%D9%88%D8%AB%D9%88%D9%82_%D8%A8%D9%87%D8%A7',

        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        hidden_category = 'تصنيفات_مخفية',

        citation_needed_templates = [
            'بحاجة لمصدر',
            'تأكيد رأي',
            'تأكيد مصدر',
            'غير موثق',
            'فشل التوثيق',
            'مصدر ناقص',
            'وثق المصدر',
        ],
    ),

    pt = dict(
        lang_name = 'Português',
        lang_dir = 'ltr',
        database = 'ptwiki_p',
        wikipedia_domain = 'pt.wikipedia.org',
        beginners_link = 'https://pt.wikipedia.org/wiki/ Ajuda:Tutorial/Referência',
        beginners_link_title = ' Ajuda:Tutorial/Referência',
        lead_section_policy_link = 'https://pt.wikipedia.org/wiki/Wikipedia:INTROREF',
        lead_section_policy_link_title = 'WP:INTROREF',

        accept_language = [
            'pt',
            'kea',
            'pt-BR',
        ],

        category_name_regexps_blacklist = [
            '^!',
        ],

        citation_needed_templates = [
            'Carece de fontes',
            'Sem-fontes',
            'Sem-fontes-bpv',
            'Sem-fontes-sobre',
        ],
        hidden_category = '!Categorias_ocultas',
    ),

    fa = dict(
        lang_name = 'فارسی',
        lang_dir = 'rtl',
        database = 'fawiki_p',
        wikipedia_domain = 'fa.wikipedia.org',
        beginners_link = 'https://fa.wikipedia.org/wiki/ویکی‌پدیا:شیوه_ارجاع_به_منابع',
        beginners_link_title = 'ویکی‌پدیا:شیوه ارجاع به منابع',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_templates = [
            'مدرک',
        ],
        hidden_category = 'رده‌های_پنهان',
    ),

    fr = dict(
        lang_name = 'Français',
        lang_dir = 'ltr',
        database = 'frwiki_p',
        wikipedia_domain = 'fr.wikipedia.org',
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
        hidden_category = 'Catégorie_cachée',
        html_css_selectors_to_strip = [
            '.bandeau-article',
            '.bandeau-section',
            '.bandeau-niveau-detail',
            '.bandeau-niveau-modere',
            '.homonymie',
        ],
    ),

    it = dict(
        lang_name = 'Italiano',
        lang_dir = 'ltr',
        database = 'itwiki_p',
        wikipedia_domain = 'it.wikipedia.org',
        beginners_link = 'https://it.wikipedia.org/wiki/Aiuto:Uso_delle_fonti',
        beginners_link_title = 'Aiuto:Uso_delle_fonti',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_templates = [
            'Citazione necessaria',
            'Senza fonte',
        ],
        hidden_category = 'Categorie_nascoste',
    ),

    pl = dict(
        lang_name = 'Polski',
        lang_dir = 'ltr',
        database = 'plwiki_p',
        wikipedia_domain = 'pl.wikipedia.org',
        beginners_link = 'https://pl.wikipedia.org/wiki/Pomoc:Przypisy',
        beginners_link_title = 'Pomoc:Przypisy',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_templates = [
            'Fakt',
        ],
        hidden_category = 'Ukryte_kategorie',
    ),

    ca = dict(
        lang_name = 'Català',
        lang_dir = 'ltr',
        database = 'cawiki_p',
        wikipedia_domain = 'ca.wikipedia.org',
        beginners_link = 'https://ca.wikipedia.org/wiki/Viquip%C3%A8dia:Guia_per_referenciar',
        beginners_link_title = 'Viquipèdia:Guia per referenciar',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_templates = [
            'Citació necessària',
            'CC',
            'CN',
        ],
        hidden_category = 'Categories_ocultes',
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

        citation_needed_templates = ['דרוש מקור'],
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
        citation_needed_templates = [
            'Añadir referencias',
            'Cita requerida'
        ],
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

        citation_needed_templates = [
            'Není ve zdroji',
            'Doplňte zdroj',
            'Fakt/dne',
        ],
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

        citation_needed_templates = [
            'kb',
            'Källa behövs',
            'Referens behövs',
        ],
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

        citation_needed_templates = [
            'Trenger referanse',
            'Referanse',
        ],
        hidden_category = 'Skjulte_kategorier',
    ),

    ne = dict(
        lang_name = 'नेपाली',
        lang_dir = 'ltr',
        database = 'newiki_p',
        wikipedia_domain = 'ne.wikipedia.org',

        beginners_link = 'https://ne.wikipedia.org/wiki/विकिपिडिया:स्रोत_उल्लेख',
        beginners_link_title = 'विकिपिडिया:स्रोत_उल्लेख',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_templates = [
            'Citation needed',
            'cn'
        ],
        hidden_category = '',
    ),

    nl = dict(
        lang_name = 'Nederlands',
        lang_dir = 'ltr',
        database = 'nlwiki_p',
        wikipedia_domain = 'nl.wikipedia.org',

        beginners_link = 'https://nl.wikipedia.org/wiki/Wikipedia:Bronvermelding',
        beginners_link_title = 'Wikipedia:Bronvermelding',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_templates = [
            'Bron?',
        ],
        hidden_category = 'Wikipedia:Verborgen_categorie',
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

        citation_needed_templates = [
            'Treng kjelde',
        ],
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

        citation_needed_templates = [
            'Lähde',
            'Lähde tarkemmin',
            'Kenen mukaan',
        ],
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
        citation_needed_templates = [
            'Belege fehlen',
        ],
        hidden_category = 'Kategorie:Versteckt',
        extract = 'section',
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

        citation_needed_templates = [
            'Εκκρεμεί παραπομπή',
        ],
        hidden_category = 'Κρυμμένες_κατηγορίες',
    ),

    hu = dict(
        lang_name = 'Magyar',
        lang_dir = 'ltr',
        database = 'huwiki_p',
        wikipedia_domain = 'hu.wikipedia.org',

        beginners_link = 'https://hu.wikipedia.org/wiki/Wikipédia:Jegyzetelés',
        beginners_link_title = 'Wikipédia:Jegyzetelés',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_templates = [
            'nincs forrás',
            'forráskérő',
            'Részben nincs forrás',
            'rossz forrás',
            'vitatott forrás',
        ],
        hidden_category = 'Rejtett_kategóriák',
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

        citation_needed_templates = [
            'Nepieciešama atsauce',
        ],
        hidden_category = 'Slēptās_kategorijas',
    ),

    ru = dict(
        lang_name = 'Русский',
        lang_dir = 'ltr',
        database = 'ruwiki_p',
        wikipedia_domain = 'ru.wikipedia.org',

        beginners_link =
        'https://ru.wikipedia.org/wiki/%D0%92%D0%B8%D0%BA%D0%B8%D0%BF%D0%B5%D0%B4%D0%B8%D1%8F:%D0%A1%D1%81%D1%8B%D0%BB%D0%BA%D0%B8_%D0%BD%D0%B0_%D0%B8%D1%81%D1%82%D0%BE%D1%87%D0%BD%D0%B8%D0%BA%D0%B8',
        beginners_link_title = 'Википедия:Ссылки_на_источники',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_templates = [
            'Нет АИ',
            'Нет АИ 2',
            'Нет источника',
        ],
        hidden_category = 'Скрытые_категории',
    ),

    ro = dict(
        lang_name = 'Română',
        lang_dir = 'ltr',
        database = 'rowiki_p',
        wikipedia_domain = 'ro.wikipedia.org',

        beginners_link = 'https://ro.wikipedia.org/wiki/Wikipedia:Citarea_surselor',
        beginners_link_title = 'Wikipedia:Citarea_surselor',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_templates = [
            'Necesită citare',
        ],
        hidden_category = 'Categorii_ascunse',
    ),

    ml = dict(
        lang_name = 'മലയാളം',
        lang_dir = 'ltr',
        database = 'mlwiki_p',
        wikipedia_domain = 'ml.wikipedia.org',

        beginners_link = 'https://ml.wikipedia.org/wiki/വിക്കിപീഡിയ:അവലംബങ്ങൾ_ഉദ്ധരിക്കേണ്ടതെങ്ങനെ',
        beginners_link_title = 'വിക്കിപീഡിയ:അവലംബങ്ങൾ ഉദ്ധരിക്കേണ്ടതെങ്ങനെ',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_templates = [
            'തെളിവ്',
        ],
        hidden_category = 'മറഞ്ഞിരിക്കുന്ന_വർഗ്ഗങ്ങൾ',
        snippet_max_size = 1000,
    ),

    ja = dict(
        lang_name = '日本語',
        lang_dir = 'ltr',
        database = 'jawiki_p',
        wikipedia_domain = 'ja.wikipedia.org',

        beginners_link = 'https://ja.wikipedia.org/wiki/Wikipedia:出典を明記する',
        beginners_link_title = 'Wikipedia:出典を明記する',

        lead_section_policy_link = 'https://ja.wikipedia.org/wiki/Wikipedia:スタイルマニュアル_(導入部)#.E5.87.BA.E5.85.B8',

        lead_section_policy_link_title = '導入部の出典',

        citation_needed_templates = [
            '出典の明記',
            '要出典',
        ],
        hidden_category = '隠しカテゴリ',

        snippet_max_size = 1000,
    ),

    zh_hant = dict(
        lang_name = '繁體中文',
        lang_dir = 'ltr',
        accept_language = [
            'zh-TW',
            'zh-HK',
            'zh-MO',
            'zh-Hant',
        ],
        database = 'zhwiki_p',
        wikipedia_domain = 'zh.wikipedia.org',
        beginners_link = 'https://zh.wikipedia.org/wiki/Wikipedia:列明来源',
        beginners_link_title = 'Wikipedia:列明來源',
        lead_section_policy_link = 'https://zh.wikipedia.org/wiki/Wikipedia:LEADCITE',
        lead_section_policy_link_title = '序言章節的引用',
        citation_needed_templates = [
            'Unreferenced',
            'Fact',
        ],
        hidden_category = '隐藏分类',
        html_parse_parameters = {
            'variant': 'zh-hant',
        },
    ),

    zh_hans = dict(
        lang_name = '简体中文',
        lang_dir = 'ltr',
        accept_language = [
            'zh-CN',
            'zh-SG',
            'zh-Hans',
        ],
        database = 'zhwiki_p',
        wikipedia_domain = 'zh.wikipedia.org',
        beginners_link = 'https://zh.wikipedia.org/wiki/Wikipedia:列明来源',
        beginners_link_title = 'Wikipedia:列明来源',
        lead_section_policy_link = 'https://zh.wikipedia.org/wiki/Wikipedia:LEADCITE',
        lead_section_policy_link_title = '序言章节的引用',
        citation_needed_templates = [
            'Unreferenced',
            'Fact',
        ],
        hidden_category = '隐藏分类',
        html_parse_parameters = {
            'variant': 'zh-hans',
        },
    ),

    ko = dict(
        lang_name = '한국어',
        lang_dir = 'ltr',

        database = 'kowiki_p',
        wikipedia_domain = 'ko.wikipedia.org',
        beginners_link = 'https://ko.wikipedia.org/wiki/위키백과:길라잡이',
        beginners_link_title = '위키백과:길라잡이',
        reliable_sources_link = 'https://ko.wikipedia.org/wiki/위키백과:신뢰할 수 있는 출처',
        lead_section_policy_link = 'https://ko.wikipedia.org/wiki/위키백과:편집 지침/도입부',
        lead_section_policy_link_title = '도입부 편집 지침',
        hidden_category = '숨은_분류',
        citation_needed_templates = [
            '출처'
        ],
    ),

    ur = dict(
        lang_name = 'اردو',
        lang_dir = 'rtl',
        database = 'urwiki_p',
        wikipedia_domain = 'ur.wikipedia.org',
        beginners_link = 'https://ur.wikipedia.org/wiki/ویکیپیڈیا:حوالہ_دہی',
        beginners_link_title = 'ویکیپیڈیا:حوالہ دہی',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',
        citation_needed_templates = [
            'حوالہ درکار',
        ],
        hidden_category = 'پوشیدہ_زمرہ_جات',
        snippet_max_size = 1200,
    ),

    uk = dict(
        lang_name = 'Українська',
        lang_dir = 'ltr',
        database = 'ukwiki_p',
        wikipedia_domain = 'uk.wikipedia.org',
        beginners_link = 'https://uk.wikipedia.org/wiki/Вікіпедія:Посилання_на_джерела/Візуальний_редактор',
        beginners_link_title = 'Як посилатись на джерела у Візуальному редакторі',
        lead_section_policy_link = 'https://uk.wikipedia.org/wiki/Вікіпедія:Посилання_на_джерела',
        lead_section_policy_link_title = 'Вікіпедія:Посилання_на_джерела',
        citation_needed_templates = [
            'Потрібне джерело',
            'Fact',
            'Fact2',
            'Немає АД',
            'Немає АД 2',
        ],
        hidden_category = 'Приховані_категорії',
    ),

    hi = dict(
        lang_name = 'हिन्दी',
        lang_dir = 'ltr',
        database = 'hiwiki_p',
        wikipedia_domain = 'hi.wikipedia.org',

        beginners_link = 'https://hi.wikipedia.org/wiki/सहायता:यथादृश्य_संपादिका_के_साथ_संदर्भ_देने_के_लिए_परिचय/१',
        beginners_link_title = 'यथादृश्य संपादिका के साथ संदर्भ देने के लिए परिचय',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_templates = [
            'उद्धरण आवश्यक',
        ],
        hidden_category = 'छुपाई_हुई_श्रेणियाँ',
    ),

    hr = dict(
        lang_name = 'Hrvatski',
        lang_dir = 'ltr',
        database = 'hrwiki_p',
        wikipedia_domain = 'hr.wikipedia.org',
        beginners_link = 'https://hr.wikipedia.org/wiki/Wikipedija:Navođenje_izvora#Kako_navesti_izvor',
        beginners_link_title = 'Kako navesti izvor',
        reliable_sources_link = 'https://hr.wikipedia.org/wiki/Wikipedija:Provjerljivost',
        lead_section_policy_link = 'https://hr.wikipedia.org/wiki/WP:NI',
        lead_section_policy_link_title = 'Wikipedija:Navođenje izvora',
        citation_needed_templates = [
            'Nedostaje izvor',
            'Bolji izvor',
            'Izvor',
            'Potrebna verifikacija',
            'Dodatno razjasniti'
        ],
        hidden_category = 'Skrivene_kategorije',
    ),

    mk = dict(
        lang_name = 'Македонски',
        lang_dir = 'ltr',
        database = 'mkwiki_p',
        wikipedia_domain = 'mk.wikipedia.org',
        reliable_sources_link = 'https://mk.wikipedia.org/wiki/%D0%92%D0%B8%D0%BA%D0%B8%D0%BF%D0%B5%D0%B4%D0%B8%D1%98%D0%B0:%D0%9F%D1%80%D0%BE%D0%B2%D0%B5%D1%80%D0%BB%D0%B8%D0%B2%D0%BE%D1%81%D1%82',
        lead_section_policy_link = 'https://mk.wikipedia.org/wiki/%D0%92%D0%B8%D0%BA%D0%B8%D0%BF%D0%B5%D0%B4%D0%B8%D1%98%D0%B0:%D0%9D%D0%B0%D0%B2%D0%B5%D0%B4%D1%83%D0%B2%D0%B0%D1%9A%D0%B5_%D0%BD%D0%B0_%D0%B8%D0%B7%D0%B2%D0%BE%D1%80%D0%B8',
        lead_section_policy_link_title = 'Википедија:Наведување на извори',
        citation_needed_templates = [
            'Се бара извор',
            'Без извори',
        ],
        hidden_category = 'Скриени_категории',
    ),

    eo = dict(
        lang_name = 'Esperanto',
        lang_dir = 'ltr',
        database = 'eowiki_p',
        wikipedia_domain = 'eo.wikipedia.org',

        reliable_sources_link = 'https://eo.wikipedia.org/wiki/Vikipedio:Kontrolebleco',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_templates = [
            'Mankas fonto',
            'Konfirmon'
        ],
        hidden_category = 'Kaŝitaj_kategorioj',
        # We get very few articles and snippets, disable the sanity check.
        min_snippets_sanity_check = 0,
        min_articles_sanity_check = 0,
    ),

    id = dict(
        lang_name = 'bahasa Indonesia',
        lang_dir = 'ltr',
        database = 'idwiki_p',
        wikipedia_domain = 'id.wikipedia.org',

        beginners_link = 'https://id.wikipedia.org/wiki/Wikipedia:Kutip_sumber_tulisan',
        beginners_link_title = 'Cara untuk menulis sumber kutipan dalam artikel',

        reliable_sources_link = 'https://id.wikipedia.org/wiki/Wikipedia:Sumber_tepercaya',

        lead_section_policy_link = 'https://id.wikipedia.org/wiki/WP:REFERENSIPEMBUKA',
        lead_section_policy_link_title = 'WP:REFERENSIPEMBUKA',

        citation_needed_templates = [
            'Butuh rujukan'
        ],

        hidden_category = 'Kategori_tersembunyi',
    ),

    eu = dict(
        lang_name = 'Euskara',
        lang_dir = 'ltr',
        database = 'euwiki_p',
        wikipedia_domain = 'eu.wikipedia.org',
        beginners_link = 'https://eu.wikipedia.org/wiki/Laguntza:Erreferentziak',
        beginners_link_title = 'Laguntza:Erreferentziak',
        lead_section_policy_link = 'https://eu.wikipedia.org/wiki/Wikipedia:Estilo_gida/Artikuluaren_sarrera',
        lead_section_policy_link_title = 'Wikipedia:Estilo gida/Artikuluaren sarrera',

        citation_needed_templates = [
            'Erref behar',
            'Erreferentzia behar ',
        ],
        hidden_category = 'Ezkutuko_kategoriak',
    ),

    sr = dict(
        lang_name = 'Српски',
        accept_language = [
            'sr-ec',
        ],
        lang_dir = 'ltr',
        database = 'srwiki_p',
        wikipedia_domain = 'sr.wikipedia.org',
        beginners_link = 'https://sr.wikipedia.org/wiki/%D0%92%D0%B8%D0%BA%D0%B8%D0%BF%D0%B5%D0%B4%D0%B8%D1%98%D0%B0:%D0%9D%D0%B0%D0%B2%D0%BE%D1%92%D0%B5%D1%9A%D0%B5_%D0%B8%D0%B7%D0%B2%D0%BE%D1%80%D0%B0',
        beginners_link_title = 'Википедија:Навођење извора',
        lead_section_policy_link = 'https://sr.wikipedia.org/wiki/ВП:ИНЛАЈН',
        lead_section_policy_link_title = 'ВП:ИНЛАЈН',

        citation_needed_templates = [
            'Чињеница',
            'без извора',
        ],
        hidden_category = 'Скривене_категорије',
    ),

    tr = dict(
        lang_name = 'Türkçe',
        lang_dir = 'ltr',
        database = 'trwiki_p',
        wikipedia_domain = 'tr.wikipedia.org',
        beginners_link = 'https://tr.wikipedia.org/wiki/Vikipedi:Kaynak_g%C3%B6sterme',
        beginners_link_title = 'Vikipedi:Kaynak gösterme',
        lead_section_policy_link = 'https://tr.wikipedia.org/wiki/VP:KG',
        lead_section_policy_link_title = 'VP:KG',

        extract = 'section',
        citation_needed_templates = [
            'Kaynaksız',
        ],
        hidden_category = 'Gizli_kategoriler',
    ),

    sk = dict(
        lang_name = 'Slovenčina',
        lang_dir = 'ltr',
        database = 'skwiki_p',
        wikipedia_domain = 'sk.wikipedia.org',
        beginners_link = 'https://sk.wikipedia.org/wiki/Wikip%C3%A9dia:Spo%C4%BEahliv%C3%A9_zdroje',
        beginners_link_title = 'Wikipédia:Spoľahlivé zdroje',
        lead_section_policy_link = 'https://sk.wikipedia.org/wiki/WP:OVER',
        lead_section_policy_link_title = 'WP:OVER',

        citation_needed_templates = [
            'Bez citácie',
        ],
        hidden_category = 'Skryté_kategórie',
    ),

    sl = dict(
        lang_name = 'Slovenščina',
        lang_dir = 'ltr',
        database = 'slwiki_p',
        wikipedia_domain = 'sl.wikipedia.org',
        beginners_link = 'https://sl.wikipedia.org/wiki/Wikipedija:Navajanje_virov',
        beginners_link_title = 'Wikipedija:Navajanje virov',
        lead_section_policy_link = 'https://sl.wikipedia.org/wiki/WP:NV',
        lead_section_policy_link_title = 'WP:NV',

        citation_needed_templates = [
            'Navedi vir',
        ],
        hidden_category = 'Skrite_kategorije',
    ),

    bg = dict(
        lang_name = 'Български',
        lang_dir = 'ltr',
        database = 'bgwiki_p',
        wikipedia_domain = 'bg.wikipedia.org',
        beginners_link = 'https://bg.wikipedia.org/wiki/%D0%A3%D0%B8%D0%BA%D0%B8%D0%BF%D0%B5%D0%B4%D0%B8%D1%8F:%D0%A6%D0%B8%D1%82%D0%B8%D1%80%D0%B0%D0%BD%D0%B5_%D0%BD%D0%B0_%D0%B8%D0%B7%D1%82%D0%BE%D1%87%D0%BD%D0%B8%D1%86%D0%B8',
        beginners_link_title = 'Уикипедия:Цитиране на източници',
        lead_section_policy_link = 'https://bg.wikipedia.org/wiki/У:ПИ',
        lead_section_policy_link_title = 'У:ПИ',

        extract = 'section',
        citation_needed_templates = [
            'без източници',
        ],
        hidden_category = 'Скрити_категории',
    ),

    be = dict(
        lang_name = 'Беларуская',
        lang_dir = 'ltr',
        database = 'bewiki_p',
        wikipedia_domain = 'be.wikipedia.org',
        beginners_link = 'https://be.wikipedia.org/wiki/%D0%92%D1%96%D0%BA%D1%96%D0%BF%D0%B5%D0%B4%D1%8B%D1%8F:%D0%A1%D0%BF%D0%B0%D1%81%D1%8B%D0%BB%D0%BA%D1%96_%D0%BD%D0%B0_%D0%BA%D1%80%D1%8B%D0%BD%D1%96%D1%86%D1%8B',
        beginners_link_title = 'Вікіпедыя:Спасылкі на крыніцы',
        lead_section_policy_link = 'https://be.wikipedia.org/wiki/ВП:СНК',
        lead_section_policy_link_title = 'ВП:СНК',

        extract = 'section',
        citation_needed_templates = [
            'НК',
        ],
        hidden_category = 'Схаваныя_катэгорыі',
    ),

    be_tarask = dict(
        lang_name = 'Беларуская (тарашкевіца)',
        accept_language = [
            'be-tarask',
        ],
        lang_dir = 'ltr',
        database = 'be_x_oldwiki_p',
        wikipedia_domain = 'be-tarask.wikipedia.org',
        beginners_link = 'https://be-tarask.wikipedia.org/wiki/%D0%92%D1%96%D0%BA%D1%96%D0%BF%D1%8D%D0%B4%D1%8B%D1%8F:%D0%A1%D0%BF%D0%B0%D1%81%D1%8B%D0%BB%D0%BA%D1%96_%D0%BD%D0%B0_%D0%BA%D1%80%D1%8B%D0%BD%D1%96%D1%86%D1%8B',
        beginners_link_title = 'Вікіпэдыя:Спасылкі на крыніцы',
        lead_section_policy_link = 'https://be-tarask.wikipedia.org/wiki/ВП:СНК',
        lead_section_policy_link_title = 'ВП:СНК',

        extract = 'section',
        citation_needed_templates = [
            'Парады артыкулу',
            'кароткі артыкул',
            'няма выяваў',
            'няма крыніцаў',
        ],
        hidden_category = 'Схаваныя_катэгорыі',
    ),

    hy = dict(
        lang_name = 'Հայերեն',
        lang_dir = 'ltr',
        database = 'hywiki_p',
        wikipedia_domain = 'hy.wikipedia.org',
        beginners_link = 'https://hy.wikipedia.org/wiki/%D5%8E%D5%AB%D6%84%D5%AB%D5%BA%D5%A5%D5%A4%D5%AB%D5%A1:%D5%80%D5%B2%D5%B8%D6%82%D5%B4_%D5%A1%D5%B2%D5%A2%D5%B5%D5%B8%D6%82%D6%80%D5%B6%D5%A5%D6%80%D5%AB%D5%B6',
        beginners_link_title = 'Վիքիպեդիա:Հղում աղբյուրներին',
        lead_section_policy_link = 'https://hy.wikipedia.org/wiki/ՎՊ:ՎԱ',
        lead_section_policy_link_title = 'ՎՊ:ՎԱ',

        citation_needed_templates = [
            'ստուգել փաստերը'
        ],
        hidden_category = 'Թաքցված_կատեգորիաներ',
    ),

    sh = dict(
        lang_name = 'Srpskohrvatski / Српскохрватски',
        lang_dir = 'ltr',
        database = 'shwiki_p',
        wikipedia_domain = 'sh.wikipedia.org',
        beginners_link = 'https://sh.wikipedia.org/wiki/Wikipedia:Navo%C4%91enje_izvora',
        beginners_link_title = 'Wikipedia:Navođenje izvora',
        lead_section_policy_link = 'https://sh.wikipedia.org/wiki/WP:NAVOD',
        lead_section_policy_link_title = 'WP:NAVOD',

        citation_needed_templates = [
            'Reference necessary',
            'Nedostaje izvor',
        ],
        hidden_category = 'Sakrivene_kategorije',
    ),

    bs = dict(
        lang_name = 'Bosanski',
        lang_dir = 'ltr',
        database = 'bswiki_p',
        wikipedia_domain = 'bs.wikipedia.org',
        beginners_link = 'https://bs.wikipedia.org/wiki/Wikipedia:Navo%C4%91enje_izvora',
        beginners_link_title = 'Wikipedia:Navođenje izvora',
        lead_section_policy_link = 'https://bs.wikipedia.org/wiki/WP:CI',
        lead_section_policy_link_title = 'WP:CI',

        extract = 'section',
        citation_needed_templates = [
            'Nedostaju izvori',
        ],
        hidden_category = 'Skrivene_kategorije',
    ),

    azb = dict(
        lang_name = 'ورکجه ویکی‌پدیا',
        lang_dir = 'rtl',
        database = 'azbwiki_p',
        wikipedia_domain = 'azb.wikipedia.org',
        beginners_link = 'https://azb.wikipedia.org/wiki/%D9%88%DB%8C%DA%A9%DB%8C%E2%80%8C%D9%BE%D8%AF%DB%8C%D8%A7:%DA%AF%D8%A6%DA%86%D8%B1%D9%84%DB%8C_%D9%82%D8%A7%DB%8C%D9%86%D8%A7%D9%82%D9%84%D8%A7%D8%B1',
        beginners_link_title = 'ویکی‌پدیا:گئچرلی قایناقلار',
        lead_section_policy_link = 'https://azb.wikipedia.org/wiki/%D9%88%DB%8C%DA%A9%DB%8C%E2%80%8C%D9%BE%D8%AF%DB%8C%D8%A7:%DB%8C%D9%88%D9%92%D8%AE%D9%84%D8%A7%D9%86%DB%8C%D9%84%D8%A7%D8%A8%DB%8C%D9%84%D8%B1%D9%84%DB%8C%DA%A9',
        lead_section_policy_link_title = 'یکی‌پدیا:یوْخلانیلابیلرلیک',

        citation_needed_templates = [
            'قایناق‌؟',
        ],
        hidden_category = 'بؤلمه:گیزلی_بؤلمه‌لر',

        # We get very few articles and snippets, disable the sanity check.
        min_snippets_sanity_check = 0,
        min_articles_sanity_check = 0,
    ),

    # bh = dict(
    #     lang_name = 'Bihari',
    #     lang_dir = 'ltr',
    #   database = 'bhwiki_p',
    #   wikipedia_domain = 'bh.wikipedia.org',
    #   beginners_link = 'https://bh.wikipedia.org/wiki/%E0%A4%B5%E0%A4%BF%E0%A4%95%E0%A4%BF%E0%A4%AA%E0%A5%80%E0%A4%A1%E0%A4%BF%E0%A4%AF%E0%A4%BE:Citing_sources',
    #   beginners_link_title = 'विकिपीडिया:Citing_sour es',
    #   lead_section_policy_link = 'https://bh.wikipedia.org/wiki/%E0%A4%B5%E0%A4%BF%E0%A4%95%E0%A4%BF%E0%A4%AA%E0%A5%80%E0%A4%A1%E0%A4%BF%E0%A4%AF%E0%A4%BE:%E0%A4%B8%E0%A4%A4%E0%A5%8D%E0%A4%AF%E0%A4%BE%E0%A4%AA%E0%A4%A8_%E0%A4%9C%E0%A5%8B%E0%A4%97',
    #   lead_section_policy_link_title = 'विकिपीडिया:सत्यापन जोग',

    #   citation_needed_templates = [
    #       'प्रमाण देईं',
    #   ],
    #   hidden_category = 'छिपावल_श्रेणी',

    #   # We get very few articles and snippets, disable the sanity check.
    #   min_snippets_sanity_check = 0,
    #   min_articles_sanity_check = 0,
    # ),

    af = dict(
        lang_name = 'Afrikaans',
        lang_dir = 'ltr',
        database = 'afwiki_p',
        wikipedia_domain = 'af.wikipedia.org',
        beginners_link = 'https://af.wikipedia.org/wiki/Wikipedia:Betroubare_bronne',
        beginners_link_title = 'Wikipedia:Betroubare_bronne',
        lead_section_policy_link = 'https://af.wikipedia.org/wiki/Wikipedia:Verifieerbaarheid',
        lead_section_policy_link_title = 'WP:VER',

        citation_needed_templates = [
            'Feit',
        ],
        hidden_category = 'Versteekte_kategorieë',
    ),

    ms = dict(
        lang_name = 'Malay',
        lang_dir = 'ltr',
        database = 'mswiki_p',
        wikipedia_domain = 'ms.wikipedia.org',
        beginners_link = 'https://ms.wikipedia.org/wiki/Wikipedia:Sumber_yang_boleh_dipercayai',
        beginners_link_title = 'Wikipedia:Sumber_yang_boleh_dipercayai',
        lead_section_policy_link = 'https://ms.wikipedia.org/wiki/Wikipedia:Pengesahan',
        lead_section_policy_link_title = 'Wikipedia:Pengesahan',

        citation_needed_templates = [
            'Citation needed'
        ],
        hidden_category = 'Kategori_tersembunyi',
    ),

    my = dict(
        lang_name = 'Burmese',
        lang_dir = 'ltr',
        database = 'mywiki_p',
        wikipedia_domain = 'my.wikipedia.org',
        beginners_link = 'https://my.wikipedia.org/wiki/%E1%80%A1%E1%80%80%E1%80%B0%E1%80%A1%E1%80%8A%E1%80%AE:%E1%80%9C%E1%80%B0%E1%80%9E%E1%80%85%E1%80%BA%E1%80%99%E1%80%BB%E1%80%AC%E1%80%B8%E1%80%A1%E1%80%90%E1%80%BD%E1%80%80%E1%80%BA_%E1%80%80%E1%80%AD%E1%80%AF%E1%80%B8%E1%80%80%E1%80%AC%E1%80%B8%E1%80%81%E1%80%BC%E1%80%84%E1%80%BA%E1%80%B8',
        beginners_link_title = 'အကူအညီ:လူသစ်များအတွက်_ကိုးကားခြင်း',
        lead_section_policy_link = 'https://my.wikipedia.org/wiki/%E1%80%9D%E1%80%AE%E1%80%80%E1%80%AE%E1%80%95%E1%80%AE%E1%80%B8%E1%80%92%E1%80%AE%E1%80%B8%E1%80%9A%E1%80%AC%E1%80%B8:%E1%80%85%E1%80%AD%E1%80%85%E1%80%85%E1%80%BA%E1%80%A1%E1%80%90%E1%80%8A%E1%80%BA%E1%80%95%E1%80%BC%E1%80%AF%E1%80%81%E1%80%B6%E1%80%94%E1%80%AD%E1%80%AF%E1%80%84%E1%80%BA%E1%80%99%E1%80%BE%E1%80%AF',
        lead_section_policy_link_title = 'ဝီကီပီးဒီးယား:စိစစ်အတည်ပြုခံနိုင်မှု',

        citation_needed_templates = [
            'Citation needed'
        ],
        hidden_category = 'ဝှက်ထားသော_ကဏ္ဍများ',
    ),

    pa = dict(
        lang_name = 'Eastern Punjabi',
        lang_dir = 'ltr',
        database = 'pawiki_p',
        wikipedia_domain = 'pa.wikipedia.org',
        beginners_link = 'https://pa.wikipedia.org/wiki/%E0%A8%AE%E0%A8%A6%E0%A8%A6:%E0%A8%B9%E0%A8%B5%E0%A8%BE%E0%A8%B2%E0%A9%87_%E0%A8%9C%E0%A9%8B%E0%A9%9C%E0%A8%A8%E0%A8%BE',
        beginners_link_title = 'ਮਦਦ:ਹਵਾਲੇ_ਜੋੜਨਾ',
        lead_section_policy_link = 'https://pa.wikipedia.org/wiki/%E0%A8%B5%E0%A8%BF%E0%A8%95%E0%A9%80%E0%A8%AA%E0%A9%80%E0%A8%A1%E0%A9%80%E0%A8%86:%E0%A8%B0%E0%A8%B8_%E0%A8%A6%E0%A9%87_%E0%A8%AE%E0%A8%BE%E0%A8%A8%E0%A8%A3_%E0%A8%AA%E0%A9%8D%E0%A8%B0%E0%A9%80%E0%A8%95%E0%A8%BF%E0%A8%B0%E0%A8%BF%E0%A8%86',
        lead_section_policy_link_title = 'ਵਿਕੀਪੀਡੀਆ:ਰਸ ਦੇ ਮਾਨਣ ਪ੍ਰੀਕਿਰਿਆ',

        citation_needed_templates = [
            'ਹਵਾਲਾ ਲੋੜੀਂਦਾ'
        ],
        hidden_category = 'ਲੁਕਵੀਆਂ_ਸ਼੍ਰੇਣੀਆਂ',
    ),

    sd = dict(
        lang_name = 'Sindhi',
        lang_dir = 'rtl',
        database = 'sdwiki_p',
        wikipedia_domain = 'sd.wikipedia.org',
        beginners_link = 'https://sd.wikipedia.org/wiki/%D9%88%DA%AA%D9%8A%D9%BE%D9%8A%DA%8A%D9%8A%D8%A7:%D9%82%D8%A7%D8%A8%D9%84_%D8%AA%D8%B5%D8%AF%D9%8A%D9%82_%D8%AD%D9%88%D8%A7%D9%84%D8%A7',
        beginners_link_title = 'وڪيپيڊيا:قابل تصديق حوالا',
        lead_section_policy_link = 'https://pa.wikipedia.org/wiki/%E0%A8%B5%E0%A8%BF%E0%A8%95%E0%A9%80%E0%A8%AA%E0%A9%80%E0%A8%A1%E0%A9%80%E0%A8%86:%E0%A8%B0%E0%A8%B8_%E0%A8%A6%E0%A9%87_%E0%A8%AE%E0%A8%BE%E0%A8%A8%E0%A8%A3_%E0%A8%AA%E0%A9%8D%E0%A8%B0%E0%A9%80%E0%A8%95%E0%A8%BF%E0%A8%B0%E0%A8%BF%E0%A8%8://sd.wikipedia.org/wiki/%D9%88%DA%AA%D9%8A%D9%BE%D9%8A%DA%8A%D9%8A%D8%A7:%D8%AB%D8%A7%D8%A8%D8%AA%D9%8A',
        lead_section_policy_link_title = 'وڪيپيڊيا:ثابتي',

        citation_needed_templates = [
            'سانچو:حوالو گهربل',
            'حوالو گھربل',
        ],
        hidden_category = 'زمرو:پوشيدهه_زمرا',

        # We get very few articles and snippets, disable the sanity check.
        min_snippets_sanity_check = 0,
        min_articles_sanity_check = 0,
    ),

    ta = dict(
        lang_name = 'Tamil',
        lang_dir = 'ltr',
        database = 'tawiki_p',
        wikipedia_domain = 'ta.wikipedia.org',
        beginners_link = 'https://ta.wikipedia.org/wiki/%E0%AE%B5%E0%AE%BF%E0%AE%95%E0%AF%8D%E0%AE%95%E0%AE%BF%E0%AE%AA%E0%AF%8D%E0%AE%AA%E0%AF%80%E0%AE%9F%E0%AE%BF%E0%AE%AF%E0%AE%BE:%E0%AE%A8%E0%AE%AE%E0%AF%8D%E0%AE%AA%E0%AE%95%E0%AE%AE%E0%AE%BE%E0%AE%A9_%E0%AE%AE%E0%AF%82%E0%AE%B2%E0%AE%99%E0%AF%8D%E0%AE%95%E0%AE%B3%E0%AF%8D',
        beginners_link_title = 'விக்கிப்பீடியா:நம்பகமான மூலங்கள்',
        lead_section_policy_link = 'https://ta.wikipedia.org/wiki/%E0%AE%B5%E0%AE%BF%E0%AE%95%E0%AF%8D%E0%AE%95%E0%AE%BF%E0%AE%AA%E0%AF%8D%E0%AE%AA%E0%AF%80%E0%AE%9F%E0%AE%BF%E0%AE%AF%E0%AE%BE:%E0%AE%AE%E0%AF%86%E0%AE%AF%E0%AF%8D%E0%AE%AF%E0%AE%B1%E0%AE%BF%E0%AE%A4%E0%AE%A9%E0%AF%8D%E0%AE%AE%E0%AF%88',
        lead_section_policy_link_title = 'விக்கிப்பீடியா:மெய்யறிதன்மை',

        citation_needed_templates = [
            'Citation needed'
        ],
        hidden_category = 'மறைக்கப்பட்ட_பகுப்புகள்',
    ),

    tl = dict(
        lang_name = 'Tagalog',
        lang_dir = 'ltr',
        database = 'tlwiki_p',
        wikipedia_domain = 'tl.wikipedia.org',
        beginners_link = 'https://tl.wikipedia.org/wiki/Wikipedia:Pagsisipi',
        beginners_link_title = 'Wikipedia:Pagsisipi',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_templates = [
            'Fact'
        ],
        hidden_category = 'Mga_nakatagong_kategorya',
    ),

     tt = dict(
        lang_name = 'Татар',
        lang_dir = 'ltr',
        database = 'ttwiki_p',
        wikipedia_domain = 'tt.wikipedia.org',

        beginners_link =
        'https://tt.wikipedia.org/wiki/%D0%92%D0%B8%D0%BA%D0%B8%D0%BF%D0%B5%D0%B4%D0%B8%D1%8F:%D0%A7%D1%8B%D0%B3%D0%B0%D0%BD%D0%B0%D0%BA%D0%BB%D0%B0%D1%80%D0%BD%D1%8B_%D0%BA%D2%AF%D1%80%D1%81%D3%99%D1%82%D2%AF',
        beginners_link_title = 'Википедия:Чыганакларны күрсәтү',
        lead_section_policy_link = '',
        lead_section_policy_link_title = '',

        citation_needed_templates = [
            'АЧ юк',
            'АЧ юк 2',
            'Чыганагы',
        ],
        accept_language = ['tt-cyrl'],
        hidden_category = 'Яшерен_төркемнәр',
    ),

    vi = dict(
        lang_name = 'tiếng Việt',
        lang_dir = 'ltr',
        database = 'viwiki_p',
        wikipedia_domain = 'vi.wikipedia.org',
        beginners_link = 'https://vi.wikipedia.org/wiki/Wikipedia:Ngu%E1%BB%93n_%C4%91%C3%A1ng_tin_c%E1%BA%ADy',
        beginners_link_title = 'Wikipedia:Nguồn đáng tin cậy',
        lead_section_policy_link = 'https://vi.wikipedia.org/wiki/Wikipedia:Th%C3%B4ng_tin_ki%E1%BB%83m_ch%E1%BB%A9ng_%C4%91%C6%B0%E1%BB%A3c',
        lead_section_policy_link_title = 'Wikipedia:Thông tin kiểm chứng được',

        citation_needed_templates = [
            'Cần chú thích'
        ],
        hidden_category = 'Thể_loại_ẩn',
    ),

    **{  # https://stackoverflow.com/questions/54974442/escape-reserved-keywords-python
    # 'as': dict(
    #   lang_name = 'অসমীয়া',
    #   lang_dir = 'ltr',
    #   database = 'aswiki_p',
    #   wikipedia_domain = 'as.wikipedia.org',
    #   beginners_link = 'https://as.wikipedia.org/wiki/%E0%A7%B1%E0%A6%BF%E0%A6%95%E0%A6%BF%E0%A6%AA%E0%A6%BF%E0%A6%A1%E0%A6%BF%E0%A6%AF%E0%A6%BC%E0%A6%BE:%E0%A6%89%E0%A7%8E%E0%A6%B8%E0%A7%B0_%E0%A6%89%E0%A6%B2%E0%A7%8D%E0%A6%B2%E0%A7%87%E0%A6%96',
    #   beginners_link_title = 'ৱিকিপিডিয়া:উৎসৰ উল্লেখ',
    #   lead_section_policy_link = 'https://as.wikipedia.org/wiki/%E0%A7%B1%E0%A6%BF%E0%A6%95%E0%A6%BF%E0%A6%AA%E0%A6%BF%E0%A6%A1%E0%A6%BF%E0%A6%AF%E0%A6%BC%E0%A6%BE:%E0%A6%AC%E0%A6%BF%E0%A6%B6%E0%A7%8D%E0%A6%AC%E0%A6%BE%E0%A6%B8%E0%A6%AF%E0%A7%8B%E0%A6%97%E0%A7%8D%E0%A6%AF%E0%A6%A4%E0%A6%BE',
    #   lead_section_policy_link_title = 'ৱিকিপিডিয়া:বিশ্বাসযোগ্যতা',

    #   citation_needed_templates = [
    #       'Citation needed',
    #   ],
    #   hidden_category = 'অদৃশ্য_শ্ৰেণীসমূহ',
    # ),

    'or': dict(
        lang_name = 'Odia',
        lang_dir = 'ltr',
        database = 'orwiki_p',
        wikipedia_domain = 'or.wikipedia.org',
        beginners_link = 'https://or.wikipedia.org/wiki/%E0%AC%89%E0%AC%87%E0%AC%95%E0%AC%BF%E0%AC%AA%E0%AC%BF%E0%AC%A1%E0%AC%BC%E0%AC%BF%E0%AC%86:Identifying_reliable_sources',
        beginners_link_title = 'ଉଇକିପିଡ଼ିଆ:Identifying_reliable_sources',
        lead_section_policy_link = 'https://or.wikipedia.org/wiki/%E0%AC%89%E0%AC%87%E0%AC%95%E0%AC%BF%E0%AC%AA%E0%AC%BF%E0%AC%A1%E0%AC%BC%E0%AC%BF%E0%AC%86:%E0%AC%AA%E0%AC%B0%E0%AC%96%E0%AC%AF%E0%AD%8B%E0%AC%97%E0%AD%8D%E0%AD%9F%E0%AC%A4%E0%AC%BE',
        lead_section_policy_link_title = 'ଉଇକିପିଡ଼ିଆ:ପରଖଯୋଗ୍ୟତା',

        citation_needed_templates = [
            'Citation needed'
        ],
        hidden_category = 'Hidden_categories',

        # We get very few articles and snippets, disable the sanity check.
        min_snippets_sanity_check = 0,
        min_articles_sanity_check = 0,
    )},
)

def _resolve_redirects_to_templates(wikipedia, templates):
    '''Given a set of templates, return all templates that redirect to them.'''
    templates = set(templates)
    params = {
        'prop': 'redirects',
        'titles': '|'.join(
            # The API resolves Template: to the relevant per-language prefix
            'Template:' + tplname for tplname in templates
        ),
        'rnamespace': 10,
    }
    for result in wikipedia.query(params):
        for page in list(result['query']['pages'].values()):
            for redirect in page.get('redirects', []):
                if ':' not in redirect['title']:
                    # Not a template?
                    continue
                tplname = redirect['title'].split(':', 1)[1]
                templates.add(tplname)
    return templates

class Config(types.SimpleNamespace):
    def enable_wikipedia_api(self):
        # This module is imported pretty often during some manual operations
        # (e.g. creating cronjobs), and yamwapi is the only third-party
        # dependency that would require us to enter the virtualenv so... as
        # a convenience hack, we avoid importing it at module level.
        import yamwapi
        self.wikipedia = yamwapi.MediaWikiAPI(
            'https://' + self.wikipedia_domain + '/w/api.php', self.user_agent)
        self.citation_needed_templates = _resolve_redirects_to_templates(
            self.wikipedia, self.citation_needed_templates)

def _inherit(base, child):
    ret = dict(base)  # shallow copy
    for k, v in child.items():
        if k in ret:
            if isinstance(v, list):
                v = ret[k] + v
            elif isinstance(v, dict):
                v = dict(ret[k], **v)
        ret[k] = v
    return ret

LANG_CODES_TO_LANG_NAMES = {
    lang_code: _LANG_CODE_TO_CONFIG[lang_code]['lang_name']
    for lang_code in _LANG_CODE_TO_CONFIG
}

LANG_CODES_TO_ACCEPT_LANGUAGE = {
    lang_code: _LANG_CODE_TO_CONFIG[lang_code].get('accept_language', [])
    for lang_code in _LANG_CODE_TO_CONFIG
}
# Ugly one-liner to check whether the different accept_language are
# disjoint, since we depend on that to redirect the user to the right
# config if no lang_code is provided in the URL.
assert len(
    set.union(set(), *list(LANG_CODES_TO_ACCEPT_LANGUAGE.values()))
) == sum(map(len, list(LANG_CODES_TO_ACCEPT_LANGUAGE.values())))

def get_global_config():
    return Config(**_GLOBAL_CONFIG)

def get_localized_config(lang_code = None):
    if lang_code is None:
        lang_code = os.getenv('CH_LANG')
    lang_config = _LANG_CODE_TO_CONFIG[lang_code]
    cfg = Config(lang_code = lang_code, **reduce(
        _inherit, [_GLOBAL_CONFIG, _BASE_LANG_CONFIG, lang_config]))
    cfg.lang_codes_to_lang_names = LANG_CODES_TO_LANG_NAMES
    return cfg
