#!/usr/bin/env python3
"""
Lead Enricher - scrapes websites to find email addresses and missing contact info.
Usage: python3 lead-enricher.py --file leads/2026-03-09-plumbers-gateshead.csv
"""

import argparse
import csv
import os
import re
import sys
import time
from urllib.request import urlopen, Request
from urllib.parse import urljoin, urlparse, quote
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser

LEADS_DIR = os.path.join(os.path.dirname(__file__), '..', 'leads')

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
PHONE_RE = re.compile(r'(\+44|0)[\s\-]?[0-9]{2,4}[\s\-]?[0-9]{3,4}[\s\-]?[0-9]{3,4}')

CONTACT_PATHS = ['/contact', '/contact-us', '/about', '/about-us', '/get-in-touch', '/reach-us']
HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}

SKIP_EMAILS = {'example@', 'noreply@', 'no-reply@', 'support@', 'info@wordpress', 'admin@'}


def fetch(url, timeout=10):
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=timeout) as r:
            raw = r.read()
            try:
                return raw.decode('utf-8')
            except UnicodeDecodeError:
                return raw.decode('latin-1', errors='ignore')
    except Exception:
        return None


def extract_emails(html, domain):
    found = set()
    for m in EMAIL_RE.findall(html):
        m = m.lower().rstrip('.')
        if any(s in m for s in SKIP_EMAILS):
            continue
        if domain and domain not in m and m.count('@') == 1:
            pass  # allow any domain — some use different email domains
        found.add(m)
    return found


def extract_phone(html):
    matches = PHONE_RE.findall(html)
    if matches:
        # return the first clean match
        p = matches[0]
        p = re.sub(r'[\s\-]', '', p)
        return p
    return None


def find_website_by_name(name, location):
    """DuckDuckGo HTML search to find a business website."""
    query = f"{name} {location} plumber"
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    html = fetch(url)
    if not html:
        return None
    # find first result URL
    urls = re.findall(r'<a[^>]+class="result__url"[^>]*>([^<]+)</a>', html)
    for u in urls[:3]:
        u = u.strip()
        if not u.startswith('http'):
            u = 'https://' + u
        # skip directory sites
        if any(d in u for d in ['yell.com', 'checkatrade', 'trustatrader', 'facebook', 'youtube', 'linkedin']):
            continue
        return u
    return None


def enrich_lead(lead):
    changes = {}
    website = lead.get('website', '').strip()
    name = lead.get('name', '')
    address = lead.get('address', '')

    # Skip merchant/supplier chains — not our target
    skip_names = ['plumbase', 'wolseley', 'graham the plumbers']
    if any(s in name.lower() for s in skip_names):
        print(f"  SKIP (supplier): {name}")
        return changes

    # Try to find website if missing
    if not website:
        print(f"  Searching for website: {name}...")
        website = find_website_by_name(name, address)
        if website:
            print(f"    Found: {website}")
            changes['website'] = website
        time.sleep(1)

    if not website:
        print(f"  No website found for: {name}")
        return changes

    domain = urlparse(website).netloc.replace('www.', '')

    # Scrape homepage first
    print(f"  Scraping: {website}")
    html = fetch(website)
    emails = set()
    phone = None

    if html:
        emails |= extract_emails(html, domain)
        if not lead.get('phone'):
            phone = extract_phone(html)

    # Try contact pages
    for path in CONTACT_PATHS:
        contact_url = urljoin(website, path)
        if contact_url == website:
            continue
        chtml = fetch(contact_url)
        if chtml:
            emails |= extract_emails(chtml, domain)
            if not phone and not lead.get('phone'):
                phone = extract_phone(chtml)
        time.sleep(0.5)

    if emails:
        best = sorted(emails)[0]  # take first alphabetically
        print(f"    Email: {best}")
        changes['email'] = best

    if phone and not lead.get('phone'):
        print(f"    Phone: {phone}")
        changes['phone'] = phone

    if not emails and not phone:
        print(f"    Nothing found on site")

    return changes


def main():
    parser = argparse.ArgumentParser(description='Enrich leads CSV with contact info')
    parser.add_argument('--file', required=True, help='CSV file to enrich (relative to leads/ dir or absolute)')
    args = parser.parse_args()

    filepath = args.file if os.path.isabs(args.file) else os.path.join(LEADS_DIR, args.file)
    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    with open(filepath, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys()) if rows else []

    print(f"Enriching {len(rows)} leads from {os.path.basename(filepath)}...\n")
    enriched = 0

    for lead in rows:
        name = lead.get('name', '')
        print(f"[{name}]")
        changes = enrich_lead(lead)
        if changes:
            lead.update(changes)
            enriched += 1
        time.sleep(1)

    # Save back
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone. Enriched {enriched}/{len(rows)} leads. Saved to {filepath}")


if __name__ == '__main__':
    main()
