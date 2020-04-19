## Citation Hunt

Citation Hunt is a simple tool for finding unsourced statements on
Wikipedia in different languages. It is hosted at
[https://citationhunt.toolforge.org](https://citationhunt.toolforge.org).

This repository contains the full server and client code. The
[scripts/](https://github.com/eggpi/citationhunt/tree/master/scripts)
directory contains all the scripts used for processing Wikipedia dumps.
Hopefully they will be illustrative and reusable for similar applications.

#### I want to help!

That's great! There are many ways you can help. Please take a look at
[CONTRIBUTING.md](https://github.com/eggpi/citationhunt/blob/master/CONTRIBUTING.md)
for guidelines and instructions.

#### Running in Toolforge

There are three major components to Citation Hunt and they are each set up in
slightly different ways in
[Toolforge](https://wikitech.wikimedia.org/wiki/Help:Toolforge):

* The HTTP serving job runs on Kubernetes.
* The jobs that update the database run on the job grid via Cron.
* The job that identifies snippets that were fixed runs continuously on the
  grid.

Moving everything to Kubernetes is tracked in [issue #134](https://github.com/eggpi/citationhunt/issues/134).

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
$ webservice --backend=kubernetes python3.5 start
```

Then, install the crontab to launch database update jobs:

```
$ (cd citationhunt; ./crontab.py | crontab)
$ crontab -l  # verify it
```

See [scripts/README.md](https://github.com/eggpi/citationhunt/blob/master/scripts/README.md)
for more information about those jobs.

Finally, submit `scripts/compute_fixed_snippets.py` as a job on the grid to
detect snippets that were fixed:

```
$ jstart -N compute_fixed_snippets $PWD/www/python/venv/bin/python3 $PWD/www/python/src/scripts/compute_fixed_snippets.py global
```
