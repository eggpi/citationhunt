## CitationHunt scripts and tools

The scripts in this directory are used to generate the CitationHunt database.

### Generating the database on Tools Labs

The `update_db_tools_labs.py` script automates the generation of the database
on Tools Labs. It is run regularly as as a cron job and needs to run from a
virtualenv.

```
/usr/bin/jsub -mem 20g -N citationhunt_update_en -once -l release=trusty \
  /data/project/citationhunt/www/python/venv/bin/python2 \
  /data/project/citationhunt/citationhunt/scripts/update_db_tools_labs.py en
```

This will automatically find and use the MySQL credentials in `~/replica.my.cnf`.

Please refer to the following section for a more detailed explanation of how the
database is generated.

### Generating the database locally

Prerequisites:

- A local installation of MySQL;
- A working Internet connection;
- The page and categorylinks SQL dumps of Wikipedia. You can find the latest
versions these for the English Wikipedia [here](https://dumps.wikimedia.org/enwiki/latest/);
- A few hours, or potentially a rainy Sunday;

The first thing to do is to import the categorylinks and page databases to MySQL. This
can be done from the MySQL console:

```
$ mysql -u root
mysql> create database enwiki_p;
mysql> use enwiki_p;
mysql> source path/to/categorylinks.sql
mysql> source path/to/page.sql
```

This will create a new database named 'enwiki_p' and populate it with tables
named 'categorylinks' and 'page'. This will take a few hours. You'll want to use
'enwiki_p' for simplicity, but that's configurable in
[../config.py](https://github.com/eggpi/citationhunt/blob/master/config.py).

We should now make sure these scripts know how to find and log in to the databases
they will use. In order to do that, you'll need a MySQL config file that gets
passed to Citation Hunt via the `REPLICA_MY_CNF` environment variable (the
default path is conveniently `~/replica.my.cnf`, for running on Toolforge).

In a local setting, you could just use something like:

    $ cat ~/replica.my.cnf
    [client]
    user='root'
    host='localhost'

From now on, the commands we'll be typing depend on the language you're
generating a database for. They expect an environment variable `CH_LANG` to be
set to a language code taken from
[../config.py](https://github.com/eggpi/citationhunt/blob/master/config.py).
Since we're dealing with English in this document, let's set the variable
accordingly:

```
$ export CH_LANG=en
```

Now, let's create all necessary databases and tables:

```
$ (cd ..; python -c 'import chdb; chdb.initialize_all_databases()')
```

Next, let's generate the list of ids of pages with unsourced statements with
`print_unsourced_pageids_from_wikipedia.py`:

```
$ ./print_unsourced_pageids_from_wikipedia.py > unsourced
```

This list should be passed to the `parse_live.py` script, which will query the
Wikipedia API for the actual content of the pages and identify snippets lacking
citations:

```
$ ./parse_live.py unsourced
```

This should take a couple of hours on a multi-core machine. If you're
impatient, you can also pass it a maximum running time in seconds using the
`--timeout` command line option.

The next thing to do is to pick which categories will get to be displayed in
CitationHunt, thus filling up the `articles_categories` table in the database.
This is done with the `assign_categories.py` script:

```
$ ./assign_categories.py
```

At the end of this step, your MySQL installation should contain a database named
`root__scratch_en` with all the tables CitationHunt needs. The
`install_new_database.py` script will atomically move these tables to a new
database named `root__citationhunt_en`, which is where the app actually expects
to find them:

```
$ ./install_new_database.py
```

And that's it! If everything went well, you can refer to the instructions in
[../README.md](https://github.com/eggpi/citationhunt/blob/master/README.md)
to run CitationHunt using your new database.
