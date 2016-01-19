#!/bin/bash

function email() {
    echo "The logs are attached." | \
        /usr/bin/mail -s "$1" -a ~/update_db_tools_labs.err \
        citationhunt.update@tools.wmflabs.org
    sleep 2m
}

truncate -s 0 update_db_tools_labs.err

xxwiki=${CH_LANG}wiki
. ~/www/python/venv/bin/activate
cd ~/www/python/src/

# FIXME user and password need to be unquoted in ~/replica.my.cnf

ch_mysql_cnf="ch.my.cnf"
if [ ! -e "$ch_mysql_cnf" -a -f ~/replica.my.cnf ]; then
    cp ~/replica.my.cnf "$ch_mysql_cnf"
    echo "host=tools-db" >> "$ch_mysql_cnf"
fi

wp_mysql_cnf="wp.my.cnf"
if [ -f ~/replica.my.cnf ]; then
    cp ~/replica.my.cnf "$wp_mysql_cnf"
    echo "host=${xxwiki}.labsdb" >> "$wp_mysql_cnf"
fi

cd scripts/

dump_base_dir=/public/dumps/public/${CH_LANG}wiki
dump_date=`ls $dump_base_dir | tail -n1`
dump_dir=$dump_base_dir/$dump_date
echo >&2 ":: latest dump is $dump_date"
pages_articles_xml_bz2=$dump_dir/${xxwiki}-$dump_date-pages-articles.xml.bz2
if [ ! -f $pages_articles_xml_bz2 ]; then
    echo >&2 "no xml.bz2 file found, maybe the dump is in progress?"
    email "Failed to find pages-articles.xml.bz2 dump file."
    exit 1
fi

echo >&2 ":: generating unsourced pageids"
./print_unsourced_pageids_from_wikipedia.py "$wp_mysql_cnf" > unsourced
if [ $? -ne 0 ]; then
    email "Failed at print_unsourced_pageids_from_wikipedia.py"
    exit 1
fi
echo >&2 ":: parsing pages-articles.xml.bz2"
./parse_pages_articles.py "$pages_articles_xml_bz2" unsourced
if [ $? -ne 0 ]; then
    email "Failed at parse_pages_articles.py"
    exit 1
fi
echo >&2 ":: assigning categories"
./assign_categories.py --max-categories=$CH_MAX_CATEGORIES \
    --mysql-config="$mysql_cnf"
if [ $? -ne 0 ]; then
    email "Failed at assign_categories.py"
    exit 1
fi
echo >&2 ":: installing new database"
./install_new_database.py
if [ $? -ne 0 ]; then
    email "Failed at install_new_database.py"
    exit 1
fi
email "All done!"
