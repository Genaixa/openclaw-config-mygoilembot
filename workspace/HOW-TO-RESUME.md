# How to Resume Work with Claude (Senior)

## Quickest way
Open a terminal and run:
```bash
claude
```
Then just say what you want to work on — e.g.:
> "GeoXperts pipeline, next step is the website"

Claude will check its memory and pick up from where we left off.

---

## If coming via OpenClaw / Junior (Telegram or terminal)
Start OpenClaw as normal. Junior can handle most things.
If you need Senior (Claude), Junior will escalate automatically or you can ask:
> "Escalate to Senior"

---

## What's already built (as of 2026-03-09)

| Thing | Where |
|---|---|
| Lead finder script | `/root/.openclaw/workspace/scripts/lead-finder.py` |
| Lead enricher | `/root/.openclaw/workspace/scripts/lead-enricher.py` |
| Email drafter | `/root/.openclaw/workspace/scripts/email-drafter.py` |
| Reply tracker | `/root/.openclaw/workspace/scripts/reply-tracker.py` |
| Current leads file | `/root/.openclaw/workspace/leads/2026-03-09-plumbers-gateshead.csv` |
| Drafted emails (local) | `/root/.openclaw/workspace/outreach/drafts/` |
| Sales cheat sheet | `/root/.openclaw/workspace/outreach/cheat-sheet.md` |
| Pipeline skill doc | `/root/.openclaw/workspace/skills/lead-finder/SKILL.md` |

## Run the full pipeline
```bash
# Step 1 — find leads
python3 scripts/lead-finder.py --trade plumber --location "Gateshead" --radius 8

# Step 2 — find emails/phones
python3 scripts/lead-enricher.py --file FILENAME.csv

# Step 3 — draft emails to Outlook
GEOXPERTS_EMAIL="growth@geoXperts.co.uk" \
GEOXPERTS_PASSWORD="L3hm@nn5" \
GEOXPERTS_IMAP_HOST="imap.one.com" \
GEOXPERTS_IMAP_PORT="993" \
python3 scripts/email-drafter.py --file FILENAME.csv

# Step 4 — check for replies (after emails sent)
GEOXPERTS_EMAIL="growth@geoXperts.co.uk" \
GEOXPERTS_PASSWORD="L3hm@nn5" \
GEOXPERTS_IMAP_HOST="imap.one.com" \
GEOXPERTS_IMAP_PORT="993" \
python3 scripts/reply-tracker.py --file FILENAME.csv
```

## Next steps (when ready)
1. Build geoxperts.co.uk website content
2. Find more leads (new trades or locations)
3. Send drafted emails from Outlook Drafts, then run reply-tracker
4. Phone/WhatsApp outreach for leads with no email
