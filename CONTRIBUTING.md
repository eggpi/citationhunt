## Contributing to Citation Hunt

### Adding a language to Citation Hunt

In order to add a new language to Citation Hunt, two steps are necessary:

- The interface needs to be translated (see below)
- Some configuration needs to be added in the code for the new language

Please check the [Meta page on Citation Hunt](https://meta.wikimedia.org/wiki/Citation_Hunt#Adding_support_to_a_new_language) to see the information
we'll need to configure the new language, and also have a look at [Setting up a local Citation Hunt](#setting-up-a-local-citation-hunt) if you'd like to try doing it yourself!

### Translating the interface

The first step to bringing Citation Hunt to a new language is to translate its
interface. If you want to help with that, please head over to
[Translate Wiki](https://translatewiki.net/w/i.php?title=Special:Translate&group=citationhunt).

### Code changes

Code changes are more than welcome too! Take a look at the
[issues](https://github.com/eggpi/citationhunt/issues), or file your own.

#### Running the tests

[![Build Status](https://travis-ci.org/eggpi/citationhunt.svg?branch=master)](https://travis-ci.org/eggpi/citationhunt)

The `run-tests.sh` script will run all tests for you. You may want to install it
as a pre-push hook on git:

```
ln -s ../../run-tests.sh .git/hooks/pre-push
```

The tests are also run by Travis-CI for pull requests.

#### Setting up a local Citation Hunt

For more technical contributions, you will likely want to set up a local
instance of CitationHunt. Let's do that.

It's highly recommended that you use a
[virtualenv](https://pypi.python.org/pypi/virtualenv) for running CitationHunt:

```
$ virtualenv ch-venv
$ cd ch-venv
$ . bin/activate
```

Dependencies are managed via a `requirements.txt` file:

```
$ git clone https://github.com/eggpi/citationhunt
$ cd citationhunt
$ pip install -r requirements.txt
```

Note: we depend on the [lxml](http://lxml.de/) package, which may require
additional dependencies that are not listed in the requirements file. For
instance, if you are using **Ubuntu** (or some derived system), you may
also need to run:

```
$ # Ubuntu only!
$ apt-get install libxml2-dev libxslt1-dev python-dev
```

to get the dependencies to install properly.

You're nearly ready to run the server, but you will need a database for it to
work. At this point, make sure you have a working local MySQL installation —
it can be something as simple as a MySQL server listening on `localhost` that
you can access as root. Then, please proceed to [Generating the database locally](https://github.com/eggpi/citationhunt/tree/master/scripts#generating-the-database-locally),
which will allow you to try Citation Hunt locally with any language.

Once the database has been generated, you're all set! Just run `app.py` and point your browser to
`localhost:5000`:

```
$ DEBUG=1 REPLICA_MY_CNF=/path/to/replica.my.cnf python app.py
```

Adding `DEBUG=1` to the environment will run the server in [Flask's debug
mode](http://flask.pocoo.org/docs/0.10/quickstart/#debug-mode) and enable HTTP
access (the default is to redirect all URLs to HTTPS, which causes certificate
errors when running locally).
