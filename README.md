## CitationHunt

CitationHunt is a simple tool for finding unsourced statements in the English
Wikipedia, currently hosted at
[https://citationhunt.herokuapp.com/](http://citationhunt.herokuapp.com/).

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
$ python app.py
```

Adding `DEBUG=1` to the environment will run the server in [Flask's debug
mode](http://flask.pocoo.org/docs/0.10/quickstart/#debug-mode).
