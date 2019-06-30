## Citation Hunt

Citation Hunt is a simple tool for finding unsourced statements on
Wikipedia in different languages. It is hosted at
[https://tools.wmflabs.org/citationhunt/](https://tools.wmflabs.org/citationhunt/).

This repository contains the full server and client code. The
[scripts/](https://github.com/eggpi/citationhunt/tree/master/scripts)
directory contains all the scripts used for processing Wikipedia dumps.
Hopefully they will be illustrative and reusable for similar applications.

#### I want to help!

That's great! There are many ways you can help. Please take a look at
[CONTRIBUTING.md](https://github.com/eggpi/citationhunt/blob/master/CONTRIBUTING.md)
for guidelines and instructions.

#### Installing on Tools Labs

Citation Hunt can be installed on Wikimedia's Tools Labs using its [specialized
support for Python uwsgi
applications](https://wikitech.wikimedia.org/wiki/Help:Tool_Labs/Web#Python_.28uwsgi.29).

After logging in to `login.tools.wmflabs.org`, run the following commands to
create the directory structure and enter the virtualenv:

```
$ mkdir www/python/
$ virtualenv --python python3 www/python/venv/
$ . www/python/venv/bin/activate
```

Now, clone this repository, point uwsgi to it and install the dependencies:

```
$ git clone https://github.com/eggpi/citationhunt.git
$ ln -s ../../citationhunt www/python/src
$ pip install -r citationhunt/requirements.txt
```

and start the webservice:

```
$ webservice2 uwsgi-python start
```

In order to gather statistics on snippets fixed through Citation Hunt, also
submit `scripts/compute_fixed_snippets.py` as a job:

```
$ jstart -N compute_fixed_snippets $PWD/www/python/venv/bin/python3 $PWD/www/python/src/scripts/compute_fixed_snippets.py global
```

You will also want to schedule cron jobs to automatically update the database
regularly. See
[scripts/README.md](https://github.com/eggpi/citationhunt/blob/master/scripts/README.md)
for more information.
