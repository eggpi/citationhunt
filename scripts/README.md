## CitationHunt scripts and tools

The scripts in this directory are used to generate the CitationHunt database.

### Prerequisites

- A local installation of MySQL;
- The pages+articles XML dump and the categorylinks SQL dump of Wikipedia.
  You can find the latest versions of both for the English Wikipedia
  [here](https://dumps.wikimedia.org/enwiki/latest/);
- A few hours, or potentially a rainy Sunday;

### Generating the database

The first thing to do is to import the categorylinks database to MySQL. This
can be done from the MySQL console:

```
$ mysql -u root wikipedia
mysql> source path/to/citationlinks.sql
```

This will create a new database named 'wikipedia' and populate it with a table
named 'citationlinks'. This may take a few hours. The database name is hardcoded
in some of these scripts, so you'll probably want to keep it.

Next, let's generate the list of ids of pages with unsourced statements with
`print_unsourced_pageids_from_wikipedia`, which is really just a wrapper around
a SQL command run against the MySQL database:

```
$ ./print_unsourced_pageids_from_wikipedia > unsourced
```

This list, along with the pages+articles dump, should be fed into
`parse_pages_articles.py`. This script will parse all pages in the list looking
for snippets lacking citations. Page and snippet information will be written to
a citationhunt.sqlite3 database file, whose schema you can peek into by looking
at `chdb.py` in the directory above. This should take about an hour on a
multi-core machine.

```
$ ./parse_pages_articles.py path/to/pages-articles.xml unsourced
```

This script will also parse all the categories in the pages+articles dump, and
will write their information (page id and category title) to a 'categories'
table in the MySQL database. However, it will not assign categories to pages;
instead, at the end of this step, each page in the database will reference a
dummy "unassigned" category. Finally, a pickled dictionary of statistics will be
dumped to a file named stats.pkl at the end of the execution. It can be
safely removed.

The final step is to pick which categories will get to be displayed in
CitationHunt, thus fixing the "unassigned" entries in the database. This can be
done with the `assign_categories.py` script:

```
$ ./assign_categories.py --max-categories=1200
```

It's usually not a good idea to assign a category to every single page in the
CitationHunt database, because that causes some awfully specific or generic
categories to be picked (plus, it takes over 30 thousand categories to do
that). Instead, CitationHunt used a fixed maximum number of categories,
controlled by the `--max-categories` parameter, and just ignores the
unclassified pages. You should play around with that number until you find a
good compromise between including more pages versus using more (potentially
bad) categories.

At the end of this step, the CitationHunt database will be ready to go -- you
can move it to the directory above and `app.py` will pick it up. The pages that
went unclassified will be kept in the database, referring to the dummy
category, and you can later re-run `assign_categories.py` on the same database
with a larger `--max-categories` to categorize them. Otherwise, if you'd like
to drop them to shrink the database, just remove the "unassigned" category and
that deletion will cascade to all relevant pages and snippets.
