#!/bin/bash
# Wrapper for launchd auto-trigger — sets PATH and checks weekday.
# launchd does not inherit the user's shell PATH.
export PATH="/Users/nicholas.lim/.local/bin:/usr/local/bin:/usr/bin:/bin"

# Only run on weekdays (1=Mon ... 5=Fri in BSD date)
DAY=$(date +%u)
if [ "$DAY" -gt 5 ]; then
    echo "$(date): Weekend — skipping daily brief." >&1
    exit 0
fi

echo "$(date): Weekday — starting daily brief."
exec /usr/bin/python3 "/Users/nicholas.lim/Library/CloudStorage/GoogleDrive-nicholas.lim@shopee.com/My Drive/Shopee/Claude/Personal Assistant/scripts/trigger.py"
