#!/usr/bin/env python3
"""
Poll Gmail every 5 minutes for 'BRIEF NOW' trigger emails.
When found: marks them read and fires trigger.py to generate the daily brief.
Runs via launchd — no terminal window needed, no Claude tokens used during polling.

Toggle off:  launchctl unload ~/Library/LaunchAgents/com.nicholas.daily-brief-poll.plist
Toggle on:   launchctl load  ~/Library/LaunchAgents/com.nicholas.daily-brief-poll.plist
View logs:   tail -f /tmp/daily-brief-poll.log
"""
import subprocess
import json
import sys
import os
import logging

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRIGGER_SCRIPT = os.path.join(SCRIPT_DIR, "trigger.py")
GWS_BIN = "/usr/local/bin/gws"
PYTHON_BIN = "/usr/bin/python3"

TRIGGER_SUBJECT = "BRIEF NOW"
TRIGGER_QUERY = f'subject:"{TRIGGER_SUBJECT}" to:nicholas.lim@shopee.com is:unread'

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


def gws_list_messages(query: str) -> list:
    """Return list of message IDs matching the Gmail search query."""
    params = json.dumps({"userId": "me", "q": query, "maxResults": 10})
    result = subprocess.run(
        [GWS_BIN, "gmail", "users", "messages", "list", "--params", params],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        log.warning("gws list failed: %s", result.stderr[:300])
        return []
    try:
        data = json.loads(result.stdout)
        return [m["id"] for m in data.get("messages", []) if "id" in m]
    except Exception as e:
        log.warning("Failed to parse gws list output: %s", e)
        return []


def gws_mark_read(message_id: str) -> bool:
    """Remove UNREAD label so the trigger email isn't picked up again."""
    params = json.dumps({"userId": "me", "id": message_id})
    body = json.dumps({"removeLabelIds": ["UNREAD"]})
    result = subprocess.run(
        [GWS_BIN, "gmail", "users", "messages", "modify",
         "--params", params, "--json", body],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        log.warning("Mark-read failed for %s: %s", message_id, result.stderr[:200])
        return False
    return True


def fire_briefing() -> bool:
    """Run trigger.py to generate the daily brief."""
    log.info("Firing daily briefing via trigger.py...")
    result = subprocess.run([PYTHON_BIN, TRIGGER_SCRIPT])
    return result.returncode == 0


def main():
    log.info("Polling Gmail for '%s' trigger...", TRIGGER_SUBJECT)
    ids = gws_list_messages(TRIGGER_QUERY)

    if not ids:
        log.info("No trigger emails found.")
        return

    log.info("Found %d trigger email(s): %s", len(ids), ids)

    for msg_id in ids:
        if gws_mark_read(msg_id):
            log.info("Marked %s as read.", msg_id)

    # Fire once regardless of how many trigger emails arrived
    success = fire_briefing()
    if success:
        log.info("Briefing completed successfully.")
    else:
        log.error("Briefing failed — check /tmp/daily-brief-poll.log for details.")


if __name__ == "__main__":
    main()
