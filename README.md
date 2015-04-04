## CitationHunt

CitationHunt is a simple tool for finding unsourced statements in the English
Wikipedia, currently hosted at
[https://tools.wmflabs.org/citationhunt/](https://tools.wmflabs.org/citationhunt/).

This repository contains the full server and client code. The
[scripts/](https://github.com/guilherme-pg/citationhunt/tree/master/scripts)
directory contains all the scripts used for processing Wikipedia dumps.
Hopefully they will be illustrative and reusable for similar applications.

### Running

It's highly recommended that you use a
[virtualenv](https://pypi.python.org/pypi/virtualenv) for running CitationHunt:

```
$ virtualenv ch-venv
$ cd ch-venv
$ . bin/activate
```

Dependencies are managed via a `requirements.txt` file:

```
$ git clone https://github.com/guilherme-pg/citationhunt
$ cd citationhunt
$ pip install -r requirements.txt
```

Once all dependencies are installed, just run `app.py` and point your browser to
`localhost:5000`:

```
$ DEBUG=1 python app.py
```

Adding `DEBUG=1` to the environment will run the server in [Flask's debug
mode](http://flask.pocoo.org/docs/0.10/quickstart/#debug-mode) and enable HTTP
access (the default is to redirect all URLs to HTTPS, which causes certificate
errors when running locally).

#### On Tools Labs

CitationHunt can be installed on Wikimedia's Tools Labs using its [specialized
support for Python uwsgi
applications](https://wikitech.wikimedia.org/wiki/Help:Tool_Labs/Web#Python_.28uwsgi.29).

After logging in to `login.tools.wmflabs.org`, run the following commands to
create the directory structure and enter the virtualenv:

```
$ mkdir www/python/
$ virtualenv www/python/venv/
$ . www/python/venv/bin/activate
```

Now, clone this repository, point uwsgi to it and install the dependencies:

```
$ git clone https://github.com/guilherme-pg/citationhunt.git
$ ln -s ../../citationhunt www/python/src
$ pip install -r citationhunt/requirements.txt
```

and start the webserver:

```
$ webservice2 uwsgi-python start
```

You will also want to schedule a cron job to automatically update the database
as new dumps are released. See
[scripts/README.md](https://github.com/guilherme-pg/citationhunt/blob/master/scripts/README.md)
for more information.
