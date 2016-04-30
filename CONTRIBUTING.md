## Contributing to Citation Hunt

### Translating the interface

The first step to bringing Citation Hunt to a new language is to translate its
interface. If you want to help with that, please head over to
[Translate Wiki](https://translatewiki.net/w/i.php?title=Special:Translate&group=citationhunt).

### Code changes

Code changes are more than welcome too! Take a look at the
[issues](https://github.com/eggpi/citationhunt/issues), or file your own!

#### Running the tests

The `run-tests.sh` script will run all tests for you. You may want to install it
as a pre-push hook on git:

```
ln -s ../../run-tests.sh .git/hooks/pre-push
```

Please make sure you run the tests before submitting pull requests.

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

You're nearly ready to run the server, but you will need a database for it to
work. At this point, make sure you have a working local MySQL installation —
it can be something as simple as a MySQL server listening on `localhost` that
you can access as root.

You could
[generate your own database](https://github.com/eggpi/citationhunt/blob/master/scripts/README.md),
which will let you try out Citation Hunt in any language, but for now, let's
kickstart the process by importing a database dump from the English Citation
Hunt.

```
$ wget https://tools.wmflabs.org/citationhunt/static/exports/en.sql.gz
$ gunzip en.sql.gz
```

The `en.sql` file we just downloaded and extracted can be imported into MySQL:

```
$ mysql -u root
mysql> create database root__citationhunt_en;
mysql> use root__citationhunt_en;
mysql> source en.sql
```

The name of the database should follow the format above, that is,
`USER__citationhunt_LANG`.

You will now need to tell the Citation Hunt server where to find this database.
For that, write a config file called `ch.my.cnf` in the root of this directory,
where `chdb.py` is. It just needs to contain the location of the MySQL server
and the credentials to use:

```
$ cat ch.my.cnf
[client]
user='root'
host='localhost'
```

You're all set! Finally, just run `app.py` and point your browser to
`localhost:5000`:

```
$ DEBUG=1 python app.py
```

Adding `DEBUG=1` to the environment will run the server in [Flask's debug
mode](http://flask.pocoo.org/docs/0.10/quickstart/#debug-mode) and enable HTTP
access (the default is to redirect all URLs to HTTPS, which causes certificate
errors when running locally).
