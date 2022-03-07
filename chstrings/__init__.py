import flask

import os
import json

def _make_petscan_url(cfg):
    language = cfg.wikipedia_domain.replace('.wikipedia.org', '')
    return (cfg.petscan_url +
        '?language=' + language +
        '&depth=' + str(cfg.petscan_depth))

def _link_start(url, target = '_blank'):
    return flask.Markup('<a target="%s" href="%s">' % (target, url))

def _link(url, title, target = "_blank"):
    return flask.Markup('%s%s</a>' % (_link_start(url, target), title))

def _preprocess_variables(config, strings):
    strings['in_page'] = \
        flask.Markup(strings['in_page']) % _link('%s', '%s')

    if config.lead_section_policy_link:
        strings['lead_section_hint'] = \
            flask.Markup(strings['lead_section_hint']) % _link(
                config.lead_section_policy_link,
                config.lead_section_policy_link_title)
    else:
        strings['lead_section_hint'] = ''

    strings['page_not_found_text'] = \
        flask.Markup(strings['page_not_found_text']) % _link(
            'https://tools.wmflabs.org/citationhunt/' + config.lang_code,
            'Citation Hunt', "_self")

    if hasattr(config, 'reliable_sources_link'):
        link_start, link_end = (
            _link_start(config.reliable_sources_link), '</a>')
    else:
        link_start = link_end = ''

    # Note that format() doesn't raise an exception if the string doesn't
    # have any formatters, so this is fine even if instructions_goal is
    # outdated and doesn't contain the {link_start}/{link_end} markers.
    strings['instructions_goal'] = flask.Markup(
        strings['instructions_goal'].format(
            link_start = link_start, link_end = link_end))

    if strings['instructions_details'].count('%s') == 3:
        beginners_hint_link = _link(
            config.beginners_link,
            config.beginners_link_title)
        # Support the extra link pre-#129.
        strings['instructions_details'] = flask.Markup(
                strings['instructions_details']) % (
                    flask.Markup('<b>' + strings['button_wikilink'] + '</b>'),
                    flask.Markup('<b>' + strings['button_next'] + '</b>'),
                    beginners_hint_link)
    else:
        # Support beginner's link, optionally.
        if hasattr(config, 'beginners_link'):
            link_start, link_end = (_link_start(config.beginners_link), '</a>')
        else:
            link_start = link_end = ''
        strings['instructions_details'] = flask.Markup(
                (strings['instructions_details'] % (
                    flask.Markup('<b>' + strings['button_wikilink'] + '</b>'),
                    flask.Markup('<b>' + strings['button_next'] + '</b>'))).format(
                        link_start = link_start, link_end = link_end))

    # We replace the URLs in the template itself
    strings['footer'] = flask.Markup(strings['footer']) % (
        strings['tooltitle'],
        _link('%s', 'Tools Labs'),
        _link('%s', 'translatewiki.net'))

    strings['leaderboard_title'] = strings['leaderboard_title'] % (
        strings['tooltitle'])
    strings['leaderboard_description'] = (
        strings['leaderboard_description'].format(
            tooltitle = strings['tooltitle'],
            days = '%s'))  # The template swaps in the actual number.

    strings['custom_intro'] = strings['custom_intro'].format(
        tooltitle = strings['tooltitle'])

    strings['import_articles_prompt'] = flask.Markup(
        strings['import_articles_prompt'].format(
            em_start = '<b>',
            em_end = '</b>'))

    strings['import_petscan_intro'] = flask.Markup(
        strings['import_petscan_intro'].format(
            em_start = '<b>',
            em_end = '</b>'))

    strings['import_petscan_prompt'] = flask.Markup(
        strings['import_petscan_prompt'].format(
            link_start = _link_start(_make_petscan_url(config)),
            link_end = '</a>'))

    strings['back_to_cancel'] = flask.Markup(
        strings['back_to_cancel'].format(
            em_start = '<b>', back = strings['back'],
            em_end = '</b>'))

    strings['custom_please_wait'] = flask.Markup(
        strings.get('custom_please_wait', '').format(
            tooltitle = strings['tooltitle']))

    strings['custom_failed'] = flask.Markup(
        strings.get('custom_failed', '').format(
            tooltitle = strings['tooltitle']))

    strings['custom_notice'] = flask.Markup(
        strings['custom_notice'].format(
            tooltitle = strings['tooltitle'],
            link_start = _link_start('/' + config.lang_code, ''),
            link_end = '</a>'))

    strings['custom_created'] = strings.get(
        'custom_created', '').format(
            tooltitle = strings['tooltitle'])

    strings['js-leaving-custom'] = (
        strings['js-leaving-custom'].format(
            tooltitle = strings['tooltitle']))

    strings['custom_end_copy_link'] = flask.Markup(
        strings['custom_end_copy_link'].format(
            link_start = _link_start('', ''),
            link_end = '</a>'))

    strings['select_articles'] = strings['select_articles'].format(
            tooltitle = strings['tooltitle'])

    strings['select_articles_prompt'] = flask.Markup(
        strings['select_articles_prompt'].format(
            em_start = '<b>', em_end = '</b>',
            tooltitle = strings['tooltitle']))

    strings['custom_import_prompt'] = (
        strings['custom_import_prompt'].format(
            tooltitle = strings['tooltitle']))

    return strings

def _partition_js_strings(strings):
    # Separate js- strings into its own sub-key. These are meant for
    # client-side use.
    strings['js'] = {}
    for k, v in list(strings.items()):
        if k.startswith('js-'):
            strings['js'][k[3:]] = strings.pop(k)

def _load_strings_for_lang_tag(lang_tag):
    strings_dir = os.path.dirname(__file__)
    json_path = os.path.join(strings_dir, lang_tag.lower() + '.json')
    with open(json_path) as json_fp:
        return json.load(json_fp)

def get_localized_strings(config, lang_tag):
    localized_strings = {}
    try:
        localized_strings = _load_strings_for_lang_tag(lang_tag)
    except:
        return localized_strings

    # Complete the strings with the fallback in case of incomplete
    # translations, but only if there is a translation at all.
    strings = _load_strings_for_lang_tag(config.fallback_lang_tag)
    strings.update(localized_strings)
    strings = _preprocess_variables(config, strings)
    _partition_js_strings(strings)
    return strings
