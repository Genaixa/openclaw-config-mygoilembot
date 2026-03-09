#!/usr/bin/env python3
"""
Email Drafter - generates personalised GEO outreach emails and saves to Outlook Drafts.
Usage: python3 email-drafter.py --file leads/2026-03-09-plumbers-gateshead.csv
"""

import argparse
import csv
import imaplib
import json
import os
import sys
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid

# Config from environment (set in openclaw.json)
EMAIL      = os.environ.get('GEOXPERTS_EMAIL', 'growth@geoXperts.co.uk')
PASSWORD   = os.environ.get('GEOXPERTS_PASSWORD', '')
IMAP_HOST  = os.environ.get('GEOXPERTS_IMAP_HOST', 'imap.one.com')
IMAP_PORT  = int(os.environ.get('GEOXPERTS_IMAP_PORT', 993))
IMAP_DRAFT = 'INBOX.Drafts'

LEADS_DIR  = os.path.join(os.path.dirname(__file__), '..', 'leads')
DRAFTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'outreach', 'drafts')

SENDER_NAME = "Naphtoli | GeoXperts"
SIGNATURE = """
Best regards,

Naphtoli
GeoXperts — AI Search Optimisation for Local Businesses
growth@geoXperts.co.uk
"""

def generate_email(lead):
    name = lead['name']
    trade = 'plumbing'  # could be dynamic later

    subject = f"Is {name} showing up when people ask ChatGPT for a {trade[:-3]}er?"

    body = f"""Hi there,

I came across {name} and wanted to reach out about something most local {trade} businesses aren't aware of yet.

When someone in your area types "best plumber near me" into ChatGPT, Google AI, or Perplexity — your business might not be showing up, even if you rank well on Google.

That's because AI search works differently. It pulls from trusted sources, reviews, and structured information — and most local businesses haven't optimised for it yet.

That's exactly what we do at GeoXperts. We help local trades businesses get recommended by AI tools — so when someone asks an AI chatbot for a plumber in your area, your name comes up.

It's early days for this, which means there's a real first-mover advantage for businesses who act now.

Would you be open to a quick 15-minute call to see if it's a good fit for {name}? No pressure — just a conversation.

{SIGNATURE}"""

    return subject, body


def save_to_imap_drafts(subject, body, to_email=None):
    """Append email to IMAP Drafts folder."""
    msg = MIMEMultipart('alternative')
    msg['From']    = f"{SENDER_NAME} <{EMAIL}>"
    msg['To']      = to_email or EMAIL
    msg['Subject'] = subject
    msg['Date']    = formatdate()
    msg['Message-ID'] = make_msgid()

    msg.attach(MIMEText(body, 'plain'))

    try:
        m = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        m.login(EMAIL, PASSWORD)
        m.append(IMAP_DRAFT, '\\Draft', imaplib.Time2Internaldate(time.time()), msg.as_bytes())
        m.logout()
        return True
    except Exception as e:
        print(f"    IMAP error: {e}")
        return False


def save_to_file(subject, body, to_name, to_email):
    """Also save a local copy."""
    os.makedirs(DRAFTS_DIR, exist_ok=True)
    slug = to_name.lower().replace(' ', '-').replace('&', 'and')[:30]
    date = datetime.now().strftime('%Y-%m-%d')
    filename = os.path.join(DRAFTS_DIR, f"{date}-{slug}.txt")
    with open(filename, 'w') as f:
        f.write(f"TO: {to_email or 'MISSING EMAIL'}\n")
        f.write(f"FROM: {EMAIL}\n")
        f.write(f"SUBJECT: {subject}\n")
        f.write("-" * 60 + "\n")
        f.write(body)
    return filename


def main():
    parser = argparse.ArgumentParser(description='Draft outreach emails for leads')
    parser.add_argument('--file', required=True, help='CSV leads file')
    parser.add_argument('--status', default='new', help='Only process leads with this status (default: new)')
    args = parser.parse_args()

    filepath = args.file if os.path.isabs(args.file) else os.path.join(LEADS_DIR, args.file)
    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    with open(filepath, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys()) if rows else []

    targets = [r for r in rows if r.get('status') == args.status and r.get('email')]
    skipped = [r for r in rows if r.get('status') == args.status and not r.get('email')]

    print(f"Found {len(targets)} leads with email | {len(skipped)} skipped (no email)\n")

    if not targets:
        print("Nothing to draft.")
        return

    if not PASSWORD:
        print("ERROR: GEOXPERTS_PASSWORD not set in environment.")
        sys.exit(1)

    drafted = 0
    for lead in targets:
        name  = lead['name']
        email = lead['email']
        print(f"Drafting: {name} <{email}>")

        subject, body = generate_email(lead)
        file_path = save_to_file(subject, body, name, email)

        ok = save_to_imap_drafts(subject, body, to_email=email)
        if ok:
            print(f"  ✓ Saved to Outlook Drafts + {file_path}")
            lead['status'] = 'drafted'
            drafted += 1
        else:
            print(f"  ✗ IMAP failed — saved locally only: {file_path}")

    # Update CSV statuses
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone. {drafted} draft(s) saved to Outlook Drafts folder.")
    if skipped:
        print(f"\nLeads with no email (need manual outreach or phone):")
        for r in skipped:
            print(f"  - {r['name']} | {r['phone'] or r['mobile'] or 'no contact'}")


if __name__ == '__main__':
    main()
