#!/bin/sh

. ~/www/python/venv/bin/activate
cd ~/www/python/src/scripts/

# FIXME user and password need to be unquoted in ~/replica.my.cnf

mysql_cnf="./ch.my.cnf"
if [ ! -e "$mysql_cnf" -a -f ~/replica.my.cnf ]; then
    cp ~/replica.my.cnf ./ch.my.cnf
    # taken from /usr/bin/sql on tools labs
    echo "host=enwiki.labsdb" >> ./ch.my.cnf
    echo "database=enwiki_p" >> ./ch.my.cnf
fi

dump_base_dir=/public/dumps/public/enwiki
dump_date=`ls $dump_base_dir | tail -n1`
dump_dir=$dump_base_dir/$dump_date
echo >&2 ":: latest dump is $dump_date"

echo >&2 ":: generating unsourced pageids"
./print_unsourced_pageids_from_wikipedia > unsourced
echo >&2 ":: parsing pages-articles.xml.bz2"
./parse_pages_articles.py $dump_dir/enwiki-$dump_date-pages-articles.xml.bz2 unsourced
echo >&2 ":: assigning categories"
./assign_categories.py --max-categories=5500 --mysql-config="$mysql_cnf"

echo >&2 ":: installing new database"
cp citationhunt.sqlite3 ../citationhunt.sqlite3
