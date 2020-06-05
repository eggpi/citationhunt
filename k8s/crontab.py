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

freq = 4  # how many days between runs, for each language
duration = 4  # how many hours between runs within a single day

# https://kubernetes.io/docs/tasks/job/automated-tasks-with-cron-jobs/
cronjob_template = '''
---
apiVersion: batch/v1beta1
kind: CronJob
metadata:
  name: citationhunt-update-{name}
  labels:
    name: citationhunt.update-en
    # The toolforge=tool label will cause $HOME and other paths to be mounted from Toolforge
    toolforge: tool
spec:
  schedule: "0 {h} {dom}-31/{freq} * *"
  jobTemplate:
    spec:
      template:
        metadata:
          labels:
            toolforge: tool
        spec:
          containers:
          - name: ch
            workingDir: /data/project/citationhunt
            image: docker-registry.tools.wmflabs.org/toolforge-python37-sssd-base:latest
            args: [
              /data/project/citationhunt/www/python/venv/bin/python3,
              /data/project/citationhunt/citationhunt/scripts/update_db_tools_labs.py,
              {lc}
            ]
            resources:
              limits:
                memory: "4Gi"
              requests:
                memory: "4Gi"
          restartPolicy: Never
  concurrencyPolicy: Replace
'''

h = 0
for lc in sorted(config.LANG_CODES_TO_LANG_NAMES):
    print(cronjob_template.format(
        lc = lc, name = lc.replace('_', '-'),
        h=(h % 24), dom=1 + (h // 24), freq=freq))
    h += duration
