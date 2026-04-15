---
name: daily-brief
description: Generate Nicholas's read-only executive daily briefing from work Gmail and the work calendar. Use only when Nicholas explicitly invokes /daily-brief or directly asks for an inbox plus calendar briefing.
argument-hint: "[optional date override or focus]"
disable-model-invocation: true
effort: high
---

# Daily Brief
Run a read-only executive briefing for Nicholas.

## Invocation notes
- `$ARGUMENTS` — optional date override, focus area, or time window. If given, it overrides the saved checkpoint.

## Hard constraints
- Never send, modify, archive, delete, label, snooze, or mark email — except for Step 9 (automated briefing delivery to nicholas.lim@shopee.com only).
- Never modify calendar events.
- Never fabricate findings or dates.

## Files
- Checkpoint: `.claude/state/daily-brief.json`
- Briefings: `briefings/YYYY-MM-DD.md`

---

## Step 1 — Determine the time window

Read `.claude/state/daily-brief.json`. Use `last_briefing_at` as the lower bound.
If missing or null, use 72 hours ago. If `$ARGUMENTS` specifies a window, use that.

State the effective window at the top of the briefing.

---

## Step 2 — Collect signals (run all queries in parallel)

Run all of the following bash commands simultaneously in a single message — do not run them sequentially.

### 2a. Gmail — targeted searches (3 parallel queries)

Use the effective lower bound as `DATE` (format: `YYYY/MM/DD`).

**Query 1 — VIP senders:**
```bash
gws gmail users messages list --params '{"userId":"me","q":"from:(shuning.wang@shopee.com OR hoi@sea.com OR tina.leeyt@shopee.com OR ray.wang01@shopee.com OR robert.liu@shopee.com OR vincent.lee@shopee.com OR jianghong.liu@shopee.com OR edison.wei@shopee.com OR wilson.hung@shopee.com) after:DATE","maxResults":30}' 2>/dev/null
```

**Query 2 — Directly addressed to Nicholas (not sent by Nicholas):**
```bash
gws gmail users messages list --params '{"userId":"me","q":"to:nicholas.lim@shopee.com after:DATE -from:nicholas.lim@shopee.com","maxResults":40}' 2>/dev/null
```

**Query 3 — Action/decision keywords:**
```bash
gws gmail users messages list --params '{"userId":"me","q":"(subject:(\"for your action\" OR \"for your approval\" OR \"action required\" OR decision OR urgent OR deadline) OR \"Hi Nicholas\" OR \"Nicholas,\") after:DATE -from:nicholas.lim@shopee.com","maxResults":20}' 2>/dev/null
```

### 2b. Calendar — today and tomorrow

```bash
gws calendar events list --params '{"calendarId":"primary","timeMin":"TODAY_DATE_TSGTZ","timeMax":"TOMORROW_DATE_TSGTZ","singleEvents":true,"orderBy":"startTime"}' 2>/dev/null
```

Where `TODAY_DATE` = today at 00:00:00+08:00 and `TOMORROW_DATE` = tomorrow+1 at 00:00:00+08:00.

---

## Step 3 — Fetch email metadata (concurrent batch)

Collect all unique message IDs from queries 1–3. Deduplicate. Then fetch metadata for all of them in a single concurrent Python call:

```bash
python3 - <<'PYEOF'
import subprocess, json, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

IDS = ["id1", "id2", ...]  # paste all unique IDs here

def fetch(msg_id):
    r = subprocess.run(
        ["gws","gmail","users","messages","get","--params",
         json.dumps({"userId":"me","id":msg_id,"format":"metadata",
                     "metadataHeaders":["From","To","Cc","Subject","Date"]})],
        capture_output=True, text=True)
    try:
        raw = r.stdout
        idx = raw.find('{')
        d = json.loads(raw[idx:]) if idx >= 0 else {}
        h = {x["name"]:x["value"] for x in d.get("payload",{}).get("headers",[])}
        return {"id":msg_id,"snippet":d.get("snippet","")[:200],
                "from":h.get("From",""),"to":h.get("To",""),
                "cc":h.get("Cc",""),"subject":h.get("Subject",""),
                "date":h.get("Date","")}
    except Exception as e:
        return {"id":msg_id,"error":str(e)[:100]}

with ThreadPoolExecutor(max_workers=12) as ex:
    results = list(ex.map(fetch, IDS))

for r in results:
    print(json.dumps(r))
PYEOF
```

### What to look for in the metadata

**Prioritise** (likely actionable):
- Nicholas in `To:` (not just `Cc:`)
- From a VIP sender
- Subject contains `action`, `approval`, `urgent`, `decision`, or `deadline`
- Snippet contains `Hi Nicholas`, `Nicholas,`, direct question, or ownership language (`can you`, `please`, `need you to`)

**Suppress** (skip unless new risk or ask):
- TestFlight builds, Zapier, newsletters, promotions
- Automated alerts with `[No Action Required]` in subject
- Recurring daily digests (KYC routine updates, SLS abnormal reports, SOUP permission alerts)
- Calendar accept/decline/propose notifications where Nicholas is the organiser
- Local Production Support Analysis reports

**Body fetch — only if needed:**
Fetch the full body only for messages where the snippet is ambiguous and the email appears P0 or P1. Use:
```bash
gws gmail users messages get --params '{"userId":"me","id":"MSG_ID","format":"full"}' 2>/dev/null | python3 -c "
import json,sys,base64
d=json.load(sys.stdin)
print('Snippet:', d.get('snippet','')[:300])
def body(p):
    if p.get('mimeType','').startswith('text/plain'):
        data=p.get('body',{}).get('data','')
        return base64.urlsafe_b64decode(data+'==').decode('utf-8','ignore')[:600] if data else ''
    for pt in p.get('parts',[]): r=body(pt);
    return r if r else ''
print('Body:', body(d.get('payload',{})))
"
```

---

## Step 4 — Drive (optional)

Skip Drive unless:
- A VIP email explicitly references a Drive file, OR
- `$ARGUMENTS` requests Drive review

If Drive is needed, run only these two queries (parallel):
```bash
# Recently modified, not owned by Nicholas
gws drive files list --params '{"q":"modifiedTime > '\''LOWER_BOUND_ISO'\'' and not '\''me'\'' in owners and (name contains '\''TWCB'\'' or sharedWithMe=true)","fields":"files(id,name,owners,modifiedTime,webViewLink,sharingUser)","pageSize":"30"}' 2>/dev/null

# TWCB keyword
gws drive files list --params '{"q":"name contains '\''TWCB'\'' and modifiedTime > '\''LOWER_BOUND_ISO'\''","fields":"files(id,name,owners,modifiedTime,webViewLink)","pageSize":"20"}' 2>/dev/null
```

---

## Step 5 — Classify by priority

| Level | Criteria |
|-------|----------|
| **P0** | Due today · Needs reply today · Meeting today needs prep · VIP direct ask with time pressure · Travel / contract / approval blocker |
| **P1** | Reply needed within 48 h · Prep needed for tomorrow · Follow-up with downside if delayed · Medium-term risk or unresolved owner |
| **P2** | Informational · Optional prep · Low-risk follow-up · Can wait beyond 2 days |

---

## Step 6 — Produce the briefing

### Structure (in order)

**1) Executive brief** — 2–4 sentences: what matters most, biggest risk, key reply/prep item.

**2) Prioritised checklist** — checkboxes grouped by P0 / P1 / P2. Each item is an action, not an observation.

**3) Today's schedule table**

| Time | Meeting | Why it matters | Prep / Notes |
|------|---------|----------------|--------------|

Flag overlaps. Flag after-hours meetings. Note any unanswered RSVPs.

**4) Action sections** (include only when relevant):
- What matters today
- What can wait
- What to reply to
- Risks / watchouts
- Prep needed for meetings
- Short reply suggestions (talking points only, not full drafts)

**Rules:**
- Bullets tight and explicit. Dates/times in SGT.
- Distinguish facts from inference. Label inferred items.
- Dedupe threads — show only the latest message per thread.
- If reply status cannot be confirmed, say `reply status unclear`.
- No padding. Convert information into decisions and actions.

---

## Step 7 — Save

1. Save briefing to `briefings/YYYY-MM-DD.md` (append with timestamp if file exists).
2. Include in file header: generated timestamp, review window, any override.
3. Update `.claude/state/daily-brief.json`:
   - `last_briefing_at` = now (SGT ISO 8601)
   - `last_successful_run_at` = now
   - `last_briefing_file` = file path

---

## Step 8 — Quality check

The briefing is done when Nicholas can immediately answer:
- What must I do today?
- Who needs a reply?
- Which meetings matter and need prep?
- What is risky or slipping?
- What can safely wait?

---

## Step 9 — Email delivery

After Step 7 (save) succeeds, convert the briefing to HTML and send it:

```bash
BRIEF_DATE=$(date +%Y-%m-%d)
BRIEF_HTML=$(python3 - <<'PYEOF'
import sys, re, pathlib, datetime

md = pathlib.Path(f"briefings/{datetime.date.today().isoformat()}.md").read_text()

def md_to_html(text):
    lines = text.split('\n')
    html = []
    in_table = False
    in_ul = False
    i = 0
    while i < len(lines):
        line = lines[i]
        # Tables
        if '|' in line and line.strip().startswith('|'):
            if not in_table:
                if in_ul: html.append('</ul>'); in_ul = False
                html.append('<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-family:sans-serif;font-size:14px">')
                in_table = True
            if re.match(r'^\|[-| :]+\|$', line.strip()):
                i += 1; continue
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            tag = 'th' if in_table and html[-1] == '<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-family:sans-serif;font-size:14px">' else 'td'
            html.append('<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in cells) + '</tr>')
            i += 1; continue
        if in_table: html.append('</table>'); in_table = False
        # Headings
        m = re.match(r'^(#{1,3})\s+(.*)', line)
        if m:
            if in_ul: html.append('</ul>'); in_ul = False
            lvl = len(m.group(1)) + 1
            html.append(f'<h{lvl} style="font-family:sans-serif">{m.group(2)}</h{lvl}>')
        # Checkboxes / bullets
        elif re.match(r'^[-*]\s+\[[ x]\]', line):
            if not in_ul: html.append('<ul style="font-family:sans-serif;font-size:14px">'); in_ul = True
            checked = 'x' in line[3]
            text = re.sub(r'^[-*]\s+\[[ x]\]\s*', '', line)
            html.append(f'<li>{"☑" if checked else "☐"} {text}</li>')
        elif re.match(r'^[-*]\s+', line):
            if not in_ul: html.append('<ul style="font-family:sans-serif;font-size:14px">'); in_ul = True
            html.append(f'<li>{line[2:].strip()}</li>')
        # Horizontal rule
        elif re.match(r'^---+$', line.strip()):
            if in_ul: html.append('</ul>'); in_ul = False
            html.append('<hr>')
        # Blank line
        elif line.strip() == '':
            if in_ul: html.append('</ul>'); in_ul = False
            html.append('<br>')
        # Plain text / bold
        else:
            if in_ul: html.append('</ul>'); in_ul = False
            line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            html.append(f'<p style="font-family:sans-serif;font-size:14px;margin:4px 0">{line}</p>')
        i += 1
    if in_ul: html.append('</ul>')
    if in_table: html.append('</table>')
    return '\n'.join(html)

print(md_to_html(md))
PYEOF
)

gws gmail +send \
  --to nicholas.lim@shopee.com \
  --subject "Daily Briefing — ${BRIEF_DATE} (SGT)" \
  --body "${BRIEF_HTML}" \
  --html
```

- Only send if the briefing file was successfully written in Step 7.
- Do not send if the briefing generation failed or produced no content.
- This is the only permitted email-sending action per CLAUDE.md.
