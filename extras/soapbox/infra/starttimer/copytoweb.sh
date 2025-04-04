#!/bin/bash

# This script copies the src/main.py script to the web server directory /var/www/html/starttimer 
# http://192.168.100.10/starttimer/main.py

SRCFILE="/var/lib/infra/starttimer/src/main.py"
DESTFILE="/var/www/html/starttimer/main.py"

if [ -f $SRCFILE ]; then
    echo "Copying $SRCFILE to $DESTFILE"
    cp $SRCFILE $DESTFILE
    if [ $? -eq 0 ]; then
        echo "Copy successful."
    else
        echo "Copy failed."
    fi
else
    echo "Source file $SRCFILE does not exist."
fi
