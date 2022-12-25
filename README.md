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

* The HTTP serving job.
* The periodic jobs that update the database.
* The continuous job that identifies snippets that were fixed.

All of them run on
[Kubernetes](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Kubernetes). The
Kubernetes configuration is in the `k8s` directory.

After logging in to `login.tools.wmflabs.org`, run the following commands to
create the directory structure and enter the virtualenv:

```
$ mkdir www/python/
$ webservice --backend=kubernetes python3.7 shell
$ python3 -m venv www/python/venv/
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
$ webservice --backend=kubernetes python3.7 start
```

Then, generate the Cron jobs for Kubernetes:

```
$ kubectl get cronjobs | tail -n +1 | grep -E -o '^citationhunt-update-[^ ]+' | xargs kubectl delete cronjob  # delete existing jobs
$ (cd citationhunt; k8s/crontab.py | kubectl apply -f -)
$ kubectl get cronjobs # verify it
```

See [scripts/README.md](https://github.com/eggpi/citationhunt/blob/master/scripts/README.md)
for more information about those jobs.

Finally, use `k8s/compute_fixed_snippets.yaml` to launch `scripts/compute_fixed_snippets.py`
to detect snippets that get fixed:

```
$ kubectl create --validate=true -f k8s/compute_fixed_snippets.yaml
```
