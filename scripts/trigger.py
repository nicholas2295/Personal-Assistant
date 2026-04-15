#!/usr/bin/env python3
"""
Manual trigger for Nicholas's daily briefing.
Usage: python3 scripts/trigger.py

Uses 'launchctl asuser 503' to run claude inside the user's session,
which gives it access to the macOS Keychain for authentication.
This is required when called from cron (which has no user session).
"""
import subprocess
import sys
import os
import tempfile
import stat
import resource

PROJECT_DIR = os.path.join(
    os.path.expanduser("~"),
    "Library/CloudStorage/GoogleDrive-nicholas.lim@shopee.com",
    "My Drive/Shopee/Claude/Personal Assistant",
)
CLAUDE_BIN = os.path.expanduser("~/.local/bin/claude")
USER_ID = "503"


def raise_fd_limit():
    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        if soft < 8192:
            resource.setrlimit(resource.RLIMIT_NOFILE, (min(hard, 65536), hard))
    except Exception:
        pass


def main():
    raise_fd_limit()
    print("Triggering daily brief...", flush=True)

    # Write a temp script to avoid quote-escaping issues with spaces in PROJECT_DIR
    shell_script = f"""#!/bin/bash
export PATH="/Users/nicholas.lim/.local/bin:/usr/local/bin:/usr/bin:/bin"
export HOME="/Users/nicholas.lim"
export USER="nicholas.lim"
export GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND=file
ulimit -n 65536
cd '{PROJECT_DIR}'
'{CLAUDE_BIN}' -p '/daily-brief'
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False, dir="/tmp") as f:
        f.write(shell_script)
        tmp_path = f.name
    os.chmod(tmp_path, stat.S_IRWXU)

    try:
        # launchctl asuser runs the command in the user's login session — has Keychain access
        result = subprocess.run(
            ["launchctl", "asuser", USER_ID, "/bin/bash", tmp_path],
            capture_output=True,
            text=True,
        )
    finally:
        os.unlink(tmp_path)

    output = (result.stdout or "") + (result.stderr or "")
    if output:
        print(output, flush=True)

    if result.returncode == 0:
        print("Daily brief completed successfully.", flush=True)
    else:
        print(f"Daily brief failed (exit code {result.returncode}).", flush=True)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
