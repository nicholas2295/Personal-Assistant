#!/bin/bash
# Wrapper for launchd — sets PATH so gws and claude are findable.
# launchd does not inherit the user's shell PATH.
export PATH="/Users/nicholas.lim/.local/bin:/usr/local/bin:/usr/bin:/bin"
exec /usr/bin/python3 "/Users/nicholas.lim/Library/CloudStorage/GoogleDrive-nicholas.lim@shopee.com/My Drive/Shopee/Claude/Personal Assistant/scripts/poll_trigger.py"
