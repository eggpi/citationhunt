#!/usr/bin/env python3

'''Crontab generator for Citation Hunt.

This outputs the schedule of database update jobs for all languages.

The runs for different languages are spread out evenly within a given day, and
the runs for a given language are spread out evenly across the days of the
month.
'''

import config

freq = 4  # how many days between runs, for each language
duration = 4  # how many hours between runs within a single day

spec_template = '0 {h} {dom}-31/{freq} * * {command}'
command_template = ' '.join([
    '/usr/bin/jsub -mem 10g -N {jobname}_{lc} -once',
    '/data/project/citationhunt/www/python/venv/bin/python2',
    '/data/project/citationhunt/citationhunt/scripts/{scriptname}',
    '{lc}'
])

h = 0
for lc in sorted(config.LANG_CODES_TO_LANG_NAMES):
    command = command_template.format(
        jobname = 'citationhunt_update', lc = lc,
        scriptname = 'update_db_tools_labs.py')
    print(spec_template.format(
        h=(h % 24), dom=1 + (h / 24), command=command, freq=freq))
    h += duration
