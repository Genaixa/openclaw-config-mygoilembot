#!/usr/bin/env python3
"""
Reply Tracker - checks inbox for replies to outreach emails.
Flags leads with no reply after 48h for WhatsApp follow-up.
Usage: python3 reply-tracker.py --file leads/2026-03-09-plumbers-gateshead.csv
"""

import argparse
import csv
import imaplib
import email
import os
import sys
from datetime import datetime, timezone, timedelta
from email.header import decode_header

EMAIL     = os.environ.get('GEOXPERTS_EMAIL', 'growth@geoXperts.co.uk')
PASSWORD  = os.environ.get('GEOXPERTS_PASSWORD', '')
IMAP_HOST = os.environ.get('GEOXPERTS_IMAP_HOST', 'imap.one.com')
IMAP_PORT = int(os.environ.get('GEOXPERTS_IMAP_PORT', 993))

LEADS_DIR = os.path.join(os.path.dirname(__file__), '..', 'leads')
FOLLOWUP_HOURS = 48


def decode_str(s):
    if not s:
        return ''
    parts = decode_header(s)
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or 'utf-8', errors='ignore'))
        else:
            result.append(part)
    return ' '.join(result)


def get_inbox_senders(imap):
    """Get all sender emails from inbox."""
    imap.select('INBOX')
    _, data = imap.search(None, 'ALL')
    senders = set()
    for num in data[0].split():
        _, msg_data = imap.fetch(num, '(RFC822.HEADER)')
        msg = email.message_from_bytes(msg_data[0][1])
        from_header = decode_str(msg.get('From', ''))
        # extract email address
        import re
        match = re.search(r'[\w.+-]+@[\w.-]+\.\w+', from_header)
        if match:
            senders.add(match.group(0).lower())
    return senders


def parse_sent_date(lead):
    """Try to get when the email was sent from the notes field."""
    notes = lead.get('notes', '')
    import re
    m = re.search(r'sent:(\d{4}-\d{2}-\d{2})', notes)
    if m:
        return datetime.strptime(m.group(1), '%Y-%m-%d').replace(tzinfo=timezone.utc)
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', required=True)
    args = parser.parse_args()

    filepath = args.file if os.path.isabs(args.file) else os.path.join(LEADS_DIR, args.file)
    with open(filepath, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys())

    # Connect and get all inbox senders
    print(f"Connecting to {IMAP_HOST}...")
    imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    imap.login(EMAIL, PASSWORD)
    inbox_senders = get_inbox_senders(imap)
    imap.logout()
    print(f"Found {len(inbox_senders)} senders in inbox.\n")

    now = datetime.now(timezone.utc)
    replied     = []
    needs_followup = []
    waiting     = []

    for lead in rows:
        if lead.get('status') not in ('contacted', 'drafted'):
            continue

        lead_email = lead.get('email', '').lower()
        name = lead.get('name', '')

        # Check if they replied
        if lead_email in inbox_senders:
            print(f"✅ REPLIED: {name} <{lead_email}>")
            lead['status'] = 'replied'
            lead['notes'] = (lead.get('notes','') + ' | reply received').strip(' |')
            replied.append(lead)
            continue

        # Check how long since sent
        sent = parse_sent_date(lead)
        if sent:
            hours_since = (now - sent).total_seconds() / 3600
            if hours_since >= FOLLOWUP_HOURS:
                print(f"⚠️  NO REPLY ({int(hours_since)}h): {name} | {lead.get('phone') or lead.get('mobile') or 'no phone'}")
                needs_followup.append(lead)
            else:
                print(f"⏳ Waiting ({int(hours_since)}h / {FOLLOWUP_HOURS}h): {name}")
                waiting.append(lead)
        else:
            # No sent date recorded — flag anyway if status is contacted
            if lead.get('status') == 'contacted':
                print(f"⚠️  NO REPLY (date unknown): {name} | {lead.get('phone') or lead.get('mobile') or 'no phone'}")
                needs_followup.append(lead)

    # Save updated statuses
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Summary
    print(f"\n{'='*50}")
    print(f"Replied:          {len(replied)}")
    print(f"Needs follow-up:  {len(needs_followup)}")
    print(f"Still waiting:    {len(waiting)}")

    if needs_followup:
        print(f"\n📱 Ready for WhatsApp/phone follow-up:")
        for l in needs_followup:
            phone = l.get('phone') or l.get('mobile') or 'no phone'
            print(f"  - {l['name']} | {phone}")
            print(f"    Message: \"Hi, Naphtoli here from GeoXperts. I sent you an email about {l['name']} showing up on ChatGPT — just making sure it didn't get lost. Happy to chat for 5 mins if useful.\"")


if __name__ == '__main__':
    main()
