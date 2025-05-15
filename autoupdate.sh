#!/bin/bash
export TZ='Australia/Melbourne'
LOGFILE=./cronlog.txt
echo "$(date) START" >> "$LOGFILE"
python ./orac_tracker/scraper.py auto >> "$LOGFILE" 2>&1
echo -e "\n---\n" >> "$LOGFILE"
