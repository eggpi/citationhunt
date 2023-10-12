#!/usr/bin/env python3

'''Crontab generator for Citation Hunt.

This outputs the schedule of database update jobs for all languages.

The runs for different languages are spread out evenly within a given day, and
the runs for a given language are spread out evenly across the days of the
month.
'''

import os
import sys
_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)

import config
import utils

# https://en.wikipedia.org/wiki/List_of_Wikipedias#Edition_details
TOP_20_LANG_CODES_BY_ARTICLE_COUNT = {
	'en', 'ceb', 'de', 'sv', 'fr', 'nl', 'ru', 'es', 'it', 'arz', 'pl',
	'ja', 'zh_hant', 'zh_hans', 'vi', 'war', 'uk', 'ar', 'pt', 'fa', 'ca',
} & config.LANG_CODES_TO_LANG_NAMES.keys()

SMALL_LANG_CODES_PER_CHUNK = 10

CHUNKS_OF_SMALLER_LANG_CODES = utils.ichunk(
    (lc for lc in sorted(config.LANG_CODES_TO_LANG_NAMES.keys())
        if lc not in TOP_20_LANG_CODES_BY_ARTICLE_COUNT),
    SMALL_LANG_CODES_PER_CHUNK)

# How many days between runs, for each language
FREQUENCY = 4

# How many hours between runs within a single day
DURATION_TOP20 = 12
DURATION_SMALLER = 4

# https://kubernetes.io/docs/tasks/job/automated-tasks-with-cron-jobs/
cronjob_template = '''
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: citationhunt-update-{name}
  labels:
    name: citationhunt.update-{name}
    # The toolforge=tool label will cause $HOME and other paths to be mounted from Toolforge
    toolforge: tool
spec:
  schedule: "8 {h} {dom}-31/{freq} * *"
  jobTemplate:
    spec:
      activeDeadlineSeconds: 86400  # 24h
      ttlSecondsAfterFinished: 21600  # 6h
      template:
        metadata:
          labels:
            toolforge: tool
        spec:
          containers:
          - name: ch
            workingDir: /data/project/citationhunt
            image: docker-registry.tools.wmflabs.org/toolforge-python39-sssd-base:latest
            args: [
              /data/project/citationhunt/www/python/venv/bin/python3,
              /data/project/citationhunt/citationhunt/scripts/update_db_tools_labs.py,
              {lc}
            ]
            resources:
              limits:
                memory: "4Gi"
              requests:
                memory: "1Gi"
          restartPolicy: Never
  concurrencyPolicy: Replace
'''

h = 0
for lc in TOP_20_LANG_CODES_BY_ARTICLE_COUNT:
    print(cronjob_template.format(
        lc = lc, name = lc.replace('_', '-'),
        h=(h % 24), dom=1 + (h // 24), freq=FREQUENCY))
    h += DURATION_TOP20

for i, chunk in enumerate(CHUNKS_OF_SMALLER_LANG_CODES):
    lang_codes = list(chunk)
    print(cronjob_template.format(
        lc = ', '.join(lang_codes), name = 'small-{}'.format(i),
        h=(h % 24), dom=1 + (h // 24), freq=FREQUENCY))
    h += DURATION_SMALLER
