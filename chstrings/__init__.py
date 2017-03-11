import flask

import os
import json

def _link_start(url, target = '_blank'):
    return flask.Markup('<a target="%s" href="%s">' % (target, url))

def _link(url, title, target = "_blank"):
    return flask.Markup('%s%s</a>' % (_link_start(url, target), title))

def _preprocess_variables(config, strings):
    strings['in_page'] = \
        flask.Markup(strings['in_page']) % _link('%s', '%s')

    strings.setdefault('tooltitle', 'Citation Hunt')

    if config.lead_section_policy_link:
        strings['lead_section_hint'] = \
            flask.Markup(strings['lead_section_hint']) % _link(
                config.lead_section_policy_link,
                config.lead_section_policy_link_title)
    else:
        strings['lead_section_hint'] = ''

    beginners_hint_link = _link(
        config.beginners_link,
        config.beginners_link_title)
    strings['beginners_hint'] = \
        flask.Markup(strings['beginners_hint']) % beginners_hint_link

    if '404' not in config.flagged_off:
        strings['page_not_found_text'] = \
            flask.Markup(strings['page_not_found_text']) % _link(
                'https://tools.wmflabs.org/citationhunt/' + config.lang_code,
                'Citation Hunt', "_self")

    strings.setdefault('instructions_goal', '')
    strings.setdefault('instructions_details', '')
    if strings['instructions_goal']:
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

    if strings['instructions_details']:
        strings['instructions_details'] = flask.Markup(
                strings['instructions_details']) % (
                    flask.Markup('<b>' + strings['button_wikilink'] + '</b>'),
                    flask.Markup('<b>' + strings['button_next'] + '</b>'),
                    beginners_hint_link)

    strings.setdefault('footer', '')
    if strings['footer']:
        # Work around for incorrect translations that contain "Citation Hunt"
        # literally, rather than a placeholder for toolname
        # FIXME Remove this once no translations have "Citation Hunt" hardcoded.
        strings['footer'] = strings['footer'].replace('Citation Hunt', '%s')

        # We replace the URLs in the template itself
        strings['footer'] = flask.Markup(strings['footer']) % (
            strings['tooltitle'],
            _link('%s', 'Tools Labs'),
            _link('%s', 'translatewiki.net'))
    return strings

def _partition_js_strings(strings):
    # Separate js- strings into its own sub-key. These are meant for
    # client-side use.
    strings['js'] = {}
    for k, v in strings.items():
        if k.startswith('js-'):
            strings['js'][k[3:]] = strings.pop(k)

def get_localized_strings(config, lang_tag):
    strings_dir = os.path.dirname(__file__)
    json_path = os.path.join(strings_dir, lang_tag.lower() + '.json')
    try:
        strings = json.load(file(json_path))
    except:
        return {}
    strings = _preprocess_variables(config, strings)
    _partition_js_strings(strings)
    return strings
