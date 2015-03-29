## CitationHunt scripts and tools

The scripts in this directory are used to generate the CitationHunt database.

### Generating the database

#### On Tools Labs

The `update_db_tools_labs.sh` script automates the generation of the database
from the latest Wikipedia dump on Tools Labs. It is run weekly as a cron job.

`$ jsub -mem 8g /path/to/update_db_tools_labs.sh`

It will automatically find and use your MySQL credentials. Note, however, that
*your user and password need to be unquoted* (that is, must not be enclosed in
'') in your `replica.my.cnf`, which may not be the case.

Please refer to the following section for a more detailed explanation of how the
database is generated.

#### On a local machine

Prerequisites:

- A local installation of MySQL;
- The pages+articles XML dump and the page and categorylinks SQL dumps of
  Wikipedia. You can find the latest versions of both for the English Wikipedia
  [here](https://dumps.wikimedia.org/enwiki/latest/);
- A few hours, or potentially a rainy Sunday;

The first thing to do is to import the categorylinks and page databases to MySQL. This
can be done from the MySQL console:

```
$ mysql -u root wikipedia
mysql> source path/to/citationlinks.sql
mysql> source path/to/page.sql
```

This will create a new database named 'wikipedia' and populate it with tables
named 'citationlinks' and 'page'. This may take a few hours. You can use any
database name you want, but make sure it's specified in a MySQL config file
that can be picked up by these scripts. The easiest way to do this is to create
a `ch.my.cnf` file in this directory like so:

```
[client]
user=root
host=localhost
database=wikipedia
```

Next, let's generate the list of ids of pages with unsourced statements with
`print_unsourced_pageids_from_wikipedia`, which is really just a wrapper around
a SQL command run against the MySQL database:

```
$ ./print_unsourced_pageids_from_wikipedia > unsourced
```

This list, along with the *compressed* pages+articles dump, should be fed into
`parse_pages_articles.py`. This script will parse all pages in the list looking
for snippets lacking citations. Page and snippet information will be written to
a citationhunt.sqlite3 database file, whose schema you can peek into by looking
at `chdb.py` in the directory above. This should take about an hour on a
multi-core machine.

```
$ ./parse_pages_articles.py path/to/pages-articles.xml.bz2 unsourced
```

It will not assign categories to pages; instead, at the end of this step, each
page in the database will reference a dummy "unassigned" category. Finally, a
pickled dictionary of statistics will be dumped to a file named stats.pkl at
the end of the execution. It can be safely removed.

The final step is to pick which categories will get to be displayed in
CitationHunt, thus fixing the "unassigned" entries in the database. This can be
done with the `assign_categories.py` script:

```
$ ./assign_categories.py --max-categories=5500
```

It's usually not a good idea to assign a category to every single page in the
CitationHunt database, because that causes some awfully specific or generic
categories to be picked (plus, it takes over 30 thousand categories to do
that). Instead, CitationHunt used a fixed maximum number of categories,
controlled by the `--max-categories` parameter, and the uncategorized snippets
are only accessible when no category is selected on the website. You should
play around with that number until you find a good compromise between including
more pages versus using more (potentially bad) categories.

At the end of this step, the CitationHunt database will be ready to go -- you
can move it to the directory above and `app.py` will pick it up. The pages that
went unclassified will be kept in the database, referring to the dummy
category, and you can later re-run `assign_categories.py` on the same database
with a larger `--max-categories` to categorize them. Otherwise, if you'd like
to drop them to shrink the database, just remove the "unassigned" category and
that deletion will cascade to all relevant pages and snippets.
