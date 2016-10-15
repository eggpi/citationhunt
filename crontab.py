#!/usr/bin/env python

'''Crontab generator for Citation Hunt.

This outputs the schedule of database update jobs for all languages.

The runs for different languages are spread out evenly within a given day, and
the runs for a given language are spread out evenly across the days of the
month.
'''

import config

freq = 4  # how many days between runs, for each language
duration = 4  # how many hours between runs within a single day

spec_template = '0 {h} {dom}/{freq} * * {command}'
command_template = ' '.join([
    '/usr/bin/jsub -mem 10g -N citationhunt_update_{lc} -once',
    '-l release=trusty',
    '/data/project/citationhunt/www/python/venv/bin/python2',
    '/data/project/citationhunt/citationhunt/scripts/update_db_tools_labs.py',
    '{lc}'
])

h = 0
for lc in sorted(config.lang_code_to_config):
    command = command_template.format(lc=lc)
    spec = spec_template.format(
        h=(h % 24), dom=1 + (h / 24), command=command, freq=freq)
    print spec + ' ' + command
    h += duration
