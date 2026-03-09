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

# Import review scraper from same directory
sys.path.insert(0, os.path.dirname(__file__))
from review_scraper import find_best_review

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
    name    = lead['name']
    website = lead.get('website', '')
    trade   = 'plumbing'

    # Try to find a customer review
    review = None
    if website:
        print(f"  Looking for reviews on {website}...")
        review = find_best_review(website)

    subject = f"{name} has great reviews — but is ChatGPT seeing them?"

    if review:
        review_para = f"""We had a look at {name} online and came across this review:

"{review}"

That's a brilliant review — the kind of thing that builds real trust. But here's the thing: most people searching for a plumber today aren't just using Google anymore. They're asking ChatGPT, Google AI Overview, Perplexity. And those tools don't see reviews the way Google does — unless your business has been specifically optimised for them."""

        plan_para = f"""That's what we do at GeoXperts. We take the authority you've already built — reviews like that one, your years of experience, your reputation — and make sure AI tools can actually read it, trust it, and recommend {name} when someone nearby asks for a plumber.

The plan is straightforward:
- We structure your existing reviews and content so AI search engines can parse them
- We build your presence in the trusted sources AI tools pull from
- We ensure when someone asks "who's a good plumber near me?" in ChatGPT or Google AI — your name comes up

This means more inbound enquiries, without paying for ads."""

    else:
        review_para = f"""We had a look at {name} online — you've clearly built a solid local reputation. But here's something most {trade} businesses don't know yet: reviews and reputation that work brilliantly on Google often don't carry over to AI search tools like ChatGPT, Google AI Overview, or Perplexity.

Those tools work differently. They pull from structured, trusted sources — and if you haven't been optimised for them, you're invisible there, even if you rank well on Google."""

        plan_para = f"""That's what we do at GeoXperts. We take the authority {name} has already built and make it readable by AI search tools — so when someone nearby asks ChatGPT "who's a good plumber?" your name comes up.

The plan is straightforward:
- We structure your content and reviews for AI readability
- We build your presence in the sources AI tools trust
- We make sure you're recommended by name, not just listed

This means more inbound enquiries, without paying for ads."""

    body = f"""Hi there,

GeoXperts helps local trades businesses get recommended by AI tools — ChatGPT, Google AI, Perplexity — the way SEO once helped them rank on Google. It's the next wave, and right now most local businesses aren't on it yet.

{review_para}

{plan_para}

It's early days, which means there's a real first-mover advantage for businesses who move now.

Would you be open to a quick 15-minute call to see if it's a fit for {name}? No pressure — just a conversation.
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
