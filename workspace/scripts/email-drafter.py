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
    trade   = lead.get('trade', 'plumbing')

    # Try to find a customer review
    review = None
    if website:
        print(f"  Looking for reviews on {website}...")
        review = find_best_review(website)

    subject = f"{name} — are your reviews showing up on ChatGPT?"

    ai_explain = """You probably know that Google has been changing rapidly — more and more searches now show an "AI Overview" at the top, and tools like ChatGPT, Perplexity, and Google AI are becoming the first place people go when they need a recommendation.

The way these AI tools work is different from traditional search. They don't just look at your website — they pull from reviews, trusted directories, and structured information about your business. Most local businesses haven't optimised for this yet, which means they're invisible to AI recommendations even if they rank well on Google."""

    if review:
        review_para = f"""We had a look at {name} online and found this review from one of your customers:

"{review}"

That's a strong recommendation — exactly the kind of thing that builds trust. But here's the problem: when someone in your area asks ChatGPT or Google AI "who's a good {trade} near me?", {name} probably won't come up. Not because you're not good enough — you clearly are. It's simply that AI assistants don't know you exist yet, so all those great reviews are going to waste."""

    else:
        review_para = f"""We had a look at {name} online — it's clear you've built up a solid local reputation. But here's the problem: when someone in your area asks ChatGPT or Google AI "who's a good {trade} near me?", {name} probably won't come up. Not because you're not good enough — it's simply that AI assistants don't know you exist yet."""

    plan_para = f"""That's what we fix. At GeoXperts, we make sure AI tools know about {name} — who you are, what you do, where you work, and how good you are — so when someone nearby asks for a recommendation, your name actually comes up.

Think of it like getting on Google back in the day. Same idea, new technology. And right now, most local trades businesses haven't done this yet — which means there's a real first-mover advantage for businesses who act now.

In practice that means:
- More people finding you when they ask an AI for a recommendation
- No extra ads, no extra spend
- Just your existing reputation, working harder for you

And once you're established in AI search, it's also much harder for competitors to catch up — so the sooner you move, the stronger your position."""

    body = f"""Hi there,

I wanted to reach out about something most local {trade} businesses aren't aware of yet.

{ai_explain}

{review_para}

{plan_para}

If it sounds interesting, you can book a free 15-minute call here — pick whatever time suits you:
👉 https://cal.com/geoxperts/discovery

No pressure at all — just a conversation.
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

    # Detect trade from filename (e.g. 2026-03-09-plumbers-gateshead.csv → plumber)
    import re as _re
    trade_match = _re.search(r'\d{4}-\d{2}-\d{2}-(\w+?)s?-', os.path.basename(filepath))
    detected_trade = trade_match.group(1) if trade_match else 'plumber'

    with open(filepath, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys()) if rows else []

    # Inject trade into each row so generate_email can use it
    for r in rows:
        r.setdefault('trade', detected_trade)

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
            today = datetime.now().strftime('%Y-%m-%d')
            lead['notes'] = (lead.get('notes','') + f' | drafted:{today}').strip(' |')
            drafted += 1
        else:
            print(f"  ✗ IMAP failed — saved locally only: {file_path}")

    # Update CSV statuses (strip injected fields not in original CSV)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone. {drafted} draft(s) saved to Outlook Drafts folder.")
    if skipped:
        print(f"\nLeads with no email (need manual outreach or phone):")
        for r in skipped:
            print(f"  - {r['name']} | {r['phone'] or r['mobile'] or 'no contact'}")


if __name__ == '__main__':
    main()
