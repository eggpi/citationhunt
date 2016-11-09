import flask

import os
import json

def _link(url, title):
    return flask.Markup(
        '<a target="_blank" href="%s">%s</a>' % (url, title))

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

    beginners_hint_link = _link(
        config.beginners_link,
        config.beginners_link_title)
    strings['beginners_hint'] = \
        flask.Markup(strings['beginners_hint']) % beginners_hint_link

    if '404' not in config.flagged_off:
        strings['page_not_found_text'] = \
            flask.Markup(strings['page_not_found_text']) % _link(
                config.lang_code, 'Citation Hunt')

    strings.setdefault('instructions_goal', '')
    strings.setdefault('instructions_details', '')
    if strings['instructions_details']:
        strings['instructions_details'] = flask.Markup(
                strings['instructions_details']) % (
                    flask.Markup('<b>' + strings['button_wikilink'] + '</b>'),
                    flask.Markup('<b>' + strings['button_next'] + '</b>'),
                    beginners_hint_link)

    strings.setdefault('footer', '')
    if strings['footer']:
        # We replace the URLs in the template itself
        strings['footer'] = flask.Markup(strings['footer']) % (
            _link('%s', 'Tools Labs'),
            _link('%s', 'translatewiki.net'))
    return strings

def get_localized_strings(config, lang_code):
    strings_dir = os.path.dirname(__file__)
    strings = json.load(file(os.path.join(strings_dir, lang_code + '.json')))
    return _preprocess_variables(config, strings)
