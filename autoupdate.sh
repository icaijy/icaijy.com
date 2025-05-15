#!/bin/bash
export TZ='Australia/Melbourne'
LOGFILE=~/icaijy.com/cronlog.txt
echo "$(date) START" >> "$LOGFILE"
python ~/icaijy.com/orac_tracker/scraper.py auto >> "$LOGFILE" 2>&1
echo -e "\n---\n" >> "$LOGFILE"
