import flask

import os
import json

def _preprocess_variables(config, strings):
    lead_section_policy_link = flask.Markup(
        '<a target="_blank" href=%s>%s</a>') % (
            config.lead_section_policy_link,
            config.lead_section_policy_link_title)
    strings['lead_section_hint'] = \
        flask.Markup(strings['lead_section_hint']) % lead_section_policy_link

    beginners_hint_link = flask.Markup(
        '<a target="_blank" href=%s>%s</a>') % (
            config.beginners_link,
            config.beginners_link_title)
    strings['beginners_hint'] = \
        flask.Markup(strings['beginners_hint']) % beginners_hint_link

    return strings

def get_localized_strings(config, lang_code):
    strings_dir = os.path.dirname(__file__)
    strings = json.load(file(os.path.join(strings_dir, lang_code + '.json')))
    return _preprocess_variables(config, strings)
