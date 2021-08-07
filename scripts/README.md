## Citation Hunt scripts and tools

The scripts in this directory are used to generate the Citation Hunt database.

### Generating the database on Tools Labs

See the [top-level README](https://github.com/eggpi/citationhunt#running-in-toolforge) for how to set up Kubernetes cron jobs to generate the database, and refer to the [Kubernetes cronjob](https://kubernetes.io/docs/tasks/job/automated-tasks-with-cron-jobs/) documentation for more general information.

Below are some more handy commands for manually operating and troubleshooting those cronjobs.

#### Manually launch a job
    $ kubectl create job --from=cronjob/citationhunt-update-it citationhunt-update-it-manual

#### Get pods for running jobs
    $ kubectl get pods --field-selector=status.phase=Running

#### Get logs from a pod
    $ kubectl logs ${POD?}

### Generating the database locally

Prerequisites:

- A local installation of MySQL;
- A working Internet connection;
- A few hours, or potentially a rainy Sunday;

The commands we'll be typing depend on the language you're
generating a database for. They expect an environment variable `CH_LANG` to be
set to a language code taken from
[../config.py](https://github.com/eggpi/citationhunt/blob/master/config.py).
Since we're dealing with English in this document, let's set the variable
accordingly:

```
$ export CH_LANG=en
```

First, we need to get access to (a copy of) the
[page](https://www.mediawiki.org/wiki/Special:MyLanguage/Manual:page_table) and
[categorylinks](https://www.mediawiki.org/wiki/Special:MyLanguage/Manual:categorylinks_table)
database tables for the Wikipedia we're using.

There are two alternatives for that:

#### Option 1: Using a SQL dump imported locally

<details>
  <summary>Click here to expand instructions.</summary>

Download the page.sql and categorylinks.sql dumps. You can find the latest
versions these for the English Wikipedia [here](https://dumps.wikimedia.org/enwiki/latest/).

From the MySQL console connected to your local database, import them:

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

Then, to ensure these scripts can find the database, create a local config file
at ~/replica.my.cnf:

```
$ cat ~/replica.my.cnf
[client]
user='root'
host='localhost'
```

</details>

#### Option 2: Connecting to live replicas using SSH local forwarding

<details>
  <summary>Click here to expand instructions.</summary>

Alternatively, you can connect from your local computer to the real database
replicas. The [Toolforge documentation](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Database#Connecting_to_the_database_replicas_from_your_own_computer)
has more details on this option.

You'll need an existing [Toolforge account](https://wikitech.wikimedia.org/wiki/Portal:Toolforge/Quickstart)
for this method.

First, copy your Toolforge replica.my.cnf locally, to ~/replica.my.cnf, and
create another mysql config that points to your local database. For example:

```
$ cat ~/ch.my.cnf
[client]
user='root'
host='localhost'
```

Then, establish a port forward to the database you're trying to access:

```
ssh -L 4711:enwiki.analytics.db.svc.wikimedia.cloud:3306 login.tools.wmflabs.org
```

Finally, set two environment variables:

- `CH_LOCAL_SSH_PORT` to the forwarded port (4711, in the example above).
- `CH_MY_CNF` to the local MySQL config (~/ch.my.cnf, in the example above).

</details>

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
Citation Hunt, thus filling up the `articles_categories` table in the database.
This is done with the `assign_categories.py` script:

```
$ ./assign_categories.py
```

At the end of this step, your MySQL installation should contain a database named
`root__scratch_en` with all the tables Citation Hunt needs. The
`install_new_database.py` script will atomically move these tables to a new
database named `root__citationhunt_en`, which is where the app actually expects
to find them:

```
$ ./install_new_database.py
```

And that's it! If everything went well, you can refer to the instructions in
[../README.md](https://github.com/eggpi/citationhunt/blob/master/README.md)
to run Citation Hunt using your new database.
