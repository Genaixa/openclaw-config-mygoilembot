# Skill: Lead Finder & Outreach

Find local trade business leads and draft personalised outreach emails.

## Full pipeline

### Step 1 — Find leads
```bash
python3 /root/.openclaw/workspace/scripts/lead-finder.py --trade plumber --location "Gateshead" --radius 8
```
Supported trades: plumber, electrician, builder, roofer, decorator, locksmith, cleaner, gardener, carpenter

### Step 2 — Enrich (find emails/phones from websites)
```bash
python3 /root/.openclaw/workspace/scripts/lead-enricher.py --file FILENAME.csv
```

### Step 3 — Draft outreach emails
```bash
GEOXPERTS_EMAIL="growth@geoXperts.co.uk" \
GEOXPERTS_PASSWORD="$GEOXPERTS_PASSWORD" \
GEOXPERTS_IMAP_HOST="imap.one.com" \
GEOXPERTS_IMAP_PORT="993" \
python3 /root/.openclaw/workspace/scripts/email-drafter.py --file FILENAME.csv
```
Drafts go to: Outlook Drafts folder + `/root/.openclaw/workspace/outreach/drafts/`

### Step 4 — Check for replies / flag follow-ups
```bash
GEOXPERTS_EMAIL="growth@geoXperts.co.uk" \
GEOXPERTS_PASSWORD="$GEOXPERTS_PASSWORD" \
GEOXPERTS_IMAP_HOST="imap.one.com" \
GEOXPERTS_IMAP_PORT="993" \
python3 /root/.openclaw/workspace/scripts/reply-tracker.py --file FILENAME.csv
```
Run this after emails have been sent (status = `contacted`).
Shows who replied, who needs a WhatsApp nudge after 48h, and drafts the follow-up message.

## Lead statuses
- `new` — just found
- `researched` — website/email looked up
- `drafted` — email drafted, awaiting send
- `contacted` — email sent
- `replied` — they responded
- `call-booked` — call scheduled
- `closed` — signed up
- `dead` — not interested

## All CSV files
Stored in: `/root/.openclaw/workspace/leads/`

## After drafting
Tell Naphtoli to check his Outlook Drafts, review and send manually.
Next step when ready: build the send + reply tracking pipeline.
