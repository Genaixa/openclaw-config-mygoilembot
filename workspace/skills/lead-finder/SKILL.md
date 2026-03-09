# Skill: Lead Finder

Find local trade business leads using OpenStreetMap data.

## When to use
When Naphtoli asks to find leads, prospects, or local businesses of a specific trade type.

## How to run

```bash
python3 /root/.openclaw/workspace/scripts/lead-finder.py --trade TRADE --location "LOCATION" --radius KM
```

**Supported trades:** plumber, electrician, builder, roofer, decorator, locksmith, cleaner, gardener, carpenter

**Examples:**
```bash
python3 /root/.openclaw/workspace/scripts/lead-finder.py --trade plumber --location "Gateshead" --radius 8
python3 /root/.openclaw/workspace/scripts/lead-finder.py --trade electrician --location "Newcastle" --radius 5
```

## Output
- CSV saved to `/root/.openclaw/workspace/leads/YYYY-MM-DD-TRADEs-LOCATION.csv`
- Columns: name, phone, mobile, email, website, address, status, notes

## After running — enrich the results
Always run the enricher immediately after finding leads:
```bash
python3 /root/.openclaw/workspace/scripts/lead-enricher.py --file FILENAME.csv
```
This scrapes each business website to find email addresses and missing phone numbers.

Then show Naphtoli the enriched summary and ask if he wants to start outreach.

## Status field
Update `status` in the CSV as leads progress:
- `new` — just found
- `researched` — website/email looked up
- `contacted` — email sent
- `replied` — they responded
- `call-booked` — call scheduled
- `closed` — signed up
- `dead` — not interested
