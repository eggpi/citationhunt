import flask

import os
import json

def _preprocess_variables(config, strings):
    in_page_link = flask.Markup(
        '<a target="_blank" href=%s>%s</a>')
    strings['in_page'] = \
        flask.Markup(strings['in_page']) % in_page_link

    if config.lead_section_policy_link:
        lead_section_policy_link = flask.Markup(
            '<a target="_blank" href=%s>%s</a>') % (
                config.lead_section_policy_link,
                config.lead_section_policy_link_title)
        strings['lead_section_hint'] = \
            flask.Markup(strings['lead_section_hint']) % \
            lead_section_policy_link
    else:
        strings['lead_section_hint'] = ''

    beginners_hint_link = flask.Markup(
        '<a target="_blank" href=%s>%s</a>') % (
            config.beginners_link,
            config.beginners_link_title)
    strings['beginners_hint'] = \
        flask.Markup(strings['beginners_hint']) % beginners_hint_link

    if '404' not in config.flagged_off:
        page_not_found_link = flask.Markup('<a href=%s>Citation Hunt</a>') % (
            config.lang_code)
        strings['page_not_found_text'] = \
            flask.Markup(strings['page_not_found_text']) % page_not_found_link

    strings.setdefault('instructions_goal', '')
    strings.setdefault('instructions_details', '')
    if strings['instructions_details']:
        strings['instructions_details'] = flask.Markup(
                strings['instructions_details']) % (
                    flask.Markup('<b>' + strings['button_wikilink'] + '</b>'),
                    flask.Markup('<b>' + strings['button_next'] + '</b>'),
                    beginners_hint_link)
    return strings

def get_localized_strings(config, lang_code):
    strings_dir = os.path.dirname(__file__)
    strings = json.load(file(os.path.join(strings_dir, lang_code + '.json')))
    return _preprocess_variables(config, strings)
