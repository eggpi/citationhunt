#!/bin/bash

# Should match the job's name in crontab
LOGFILE=citationhunt_update_${CH_LANG}

function email() {
    cp ~/$LOGFILE.err ~/$LOGFILE.txt
    echo "The logs are attached." | \
        /usr/bin/mail -s "$1" -a ~/$LOGFILE.txt \
        citationhunt.update@tools.wmflabs.org
    rm ~/$LOGFILE.txt
    sleep 2m
}

truncate -s 0 $LOGFILE.err

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

echo >&2 ":: generating unsourced pageids"
./print_unsourced_pageids_from_wikipedia.py "$wp_mysql_cnf" > unsourced
if [ $? -ne 0 ]; then
    email "Failed at print_unsourced_pageids_from_wikipedia.py"
    exit 1
fi
echo >&2 ":: parsing articles"
./parse_live.py unsourced
if [ $? -ne 0 ]; then
    email "Failed at parse_live.py"
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
