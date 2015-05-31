## CitationHunt scripts and tools

The scripts in this directory are used to generate the CitationHunt database.

### Generating the database on Tools Labs

The `update_db_tools_labs.sh` script automates the generation of the database
from the latest Wikipedia dump on Tools Labs. It is run weekly as a cron job.

`$ jsub -mem 10g /path/to/update_db_tools_labs.sh`

This will automatically find and use the MySQL credentials in `~/replica.my.cnf`.

Please refer to the following section for a more detailed explanation of how the
database is generated.

### Generating the database locally

Prerequisites:

- A local installation of MySQL;
- The pages+articles XML dump and the page and categorylinks SQL dumps of
  Wikipedia. You can find the latest versions of both for the English Wikipedia
  [here](https://dumps.wikimedia.org/enwiki/latest/);
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
'enwiki_p' as the database, as it is hardcoded in these scripts.

Next, let's generate the list of ids of pages with unsourced statements with
`print_unsourced_pageids_from_wikipedia.py`:

```
$ ./print_unsourced_pageids_from_wikipedia > unsourced
```

This list, along with the *compressed* pages+articles dump, should be fed into
`parse_pages_articles.py`. This script will parse all pages in the list looking
for snippets lacking citations. This should take a couple of hours on a
multi-core machine.

```
$ ./parse_pages_articles.py path/to/pages-articles.xml.bz2 unsourced
```

At the end of this step, a pickled dictionary of statistics will be dumped to a
file named `stats.pkl`. It can be safely removed.

The next thing to do is to pick which categories will get to be displayed in
CitationHunt, thus filling up the `articles_categories` table in the database.
This is done with the `assign_categories.py` script:

```
$ ./assign_categories.py --max-categories=5500
```

It's usually not a good idea to assign a category to every single page in the
CitationHunt database, because that causes some awfully specific or generic
categories to be picked (plus, it takes over 30 thousand categories to do
that).  Instead, CitationHunt used a fixed maximum number of categories,
controlled by the `--max-categories` parameter, and the uncategorized snippets
are only accessible when no category is selected on the website.

You should play around with that number until you find a good compromise
between categorizing more articles and using more (potentially bad) categories.
The pages that went unclassified will be kept in the database, and you can
later re-run `assign_categories.py` on the same database with a larger
`--max-categories` to categorize them.

At the end of this step, your MySQL installation should contain a database named
`root__scratch` with all the tables CitationHunt needs. The
`install_new_database.py` script will atomically move these tables to a new
database named `root__citationhunt`, which is where the app actually expects to
find them:

```
$ ./install_new_database.py
```

And that's it! If everything went well, you can refer to the instructions in
the above directory's
[README.md](https://github.com/guilherme-pg/citationhunt/blob/master/README.md)
to run CitationHunt using your new database.
