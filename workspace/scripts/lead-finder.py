#!/usr/bin/env python3
"""
Lead Finder - finds local trade businesses using OpenStreetMap data.
Usage: python3 lead-finder.py --trade plumber --location "Gateshead" --radius 10
Output: CSV saved to /root/.openclaw/workspace/leads/
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.parse import urlencode, quote
from urllib.error import URLError

LEADS_DIR = os.path.join(os.path.dirname(__file__), '..', 'leads')

TRADE_TAGS = {
    'plumber':      [('craft', 'plumber'), ('shop', 'plumbing')],
    'electrician':  [('craft', 'electrician')],
    'builder':      [('craft', 'builder'), ('craft', 'construction')],
    'roofer':       [('craft', 'roofer'), ('craft', 'roofing')],
    'decorator':    [('craft', 'painter'), ('craft', 'decorator')],
    'locksmith':    [('craft', 'locksmith')],
    'cleaner':      [('craft', 'cleaning')],
    'gardener':     [('craft', 'gardener'), ('craft', 'landscaping')],
    'carpenter':    [('craft', 'carpenter'), ('craft', 'joiner')],
}


def geocode(location):
    """Get bounding box for a location using Nominatim."""
    url = f"https://nominatim.openstreetmap.org/search?q={quote(location)}&format=json&limit=1"
    req = Request(url, headers={'User-Agent': 'MyGoilemBot-LeadFinder/1.0'})
    try:
        with urlopen(req, timeout=10) as r:
            results = json.loads(r.read())
        if not results:
            print(f"ERROR: Could not geocode '{location}'")
            sys.exit(1)
        bbox = results[0]['boundingbox']  # [south, north, west, east]
        name = results[0]['display_name']
        print(f"Location: {name}")
        return float(bbox[0]), float(bbox[2]), float(bbox[1]), float(bbox[3])
    except URLError as e:
        print(f"ERROR: Geocoding failed: {e}")
        sys.exit(1)


def expand_bbox(s, w, n, e, km):
    """Expand bounding box by roughly N km."""
    deg = km / 111.0
    return s - deg, w - deg * 1.5, n + deg, e + deg * 1.5


def query_overpass(trade, s, w, n, e):
    """Query Overpass API for businesses of a given trade type."""
    tags = TRADE_TAGS.get(trade.lower(), [('craft', trade.lower())])
    bbox = f"{s},{w},{n},{e}"

    parts = []
    for key, val in tags:
        parts.append(f'node["{key}"="{val}"]({bbox});')
        parts.append(f'way["{key}"="{val}"]({bbox});')

    query = f'[out:json][timeout:25];({" ".join(parts)});out center;'

    url = "https://overpass-api.de/api/interpreter"
    data = urlencode({'data': query}).encode()
    req = Request(url, data=data, headers={'User-Agent': 'MyGoilemBot-LeadFinder/1.0'})

    try:
        with urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except URLError as e:
        print(f"ERROR: Overpass query failed: {e}")
        sys.exit(1)


def parse_results(elements):
    leads = []
    for e in elements:
        tags = e.get('tags', {})
        name = tags.get('name', '').strip()
        if not name:
            continue

        # Get coordinates
        if e['type'] == 'node':
            lat, lon = e.get('lat'), e.get('lon')
        else:
            center = e.get('center', {})
            lat, lon = center.get('lat'), center.get('lon')

        leads.append({
            'name':    name,
            'phone':   tags.get('phone', tags.get('contact:phone', '')).strip(),
            'mobile':  tags.get('mobile', tags.get('contact:mobile', '')).strip(),
            'email':   tags.get('email', tags.get('contact:email', '')).strip(),
            'website': tags.get('website', tags.get('contact:website', '')).strip(),
            'address': ', '.join(filter(None, [
                tags.get('addr:housenumber', ''),
                tags.get('addr:street', ''),
                tags.get('addr:city', ''),
                tags.get('addr:postcode', ''),
            ])),
            'lat': lat,
            'lon': lon,
            'osm_id': e.get('id', ''),
            'status': 'new',
            'notes': '',
        })
    return leads


def save_csv(leads, trade, location):
    os.makedirs(LEADS_DIR, exist_ok=True)
    date = datetime.now().strftime('%Y-%m-%d')
    slug = location.lower().replace(' ', '-')
    filename = os.path.join(LEADS_DIR, f"{date}-{trade}s-{slug}.csv")

    fields = ['name', 'phone', 'mobile', 'email', 'website', 'address', 'lat', 'lon', 'osm_id', 'status', 'notes']
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(leads)

    return filename


def main():
    parser = argparse.ArgumentParser(description='Find local trade leads')
    parser.add_argument('--trade',    default='plumber',   help='Trade type (plumber, electrician, etc.)')
    parser.add_argument('--location', default='Gateshead', help='Location to search')
    parser.add_argument('--radius',   type=int, default=5, help='Search radius in km (default: 5)')
    args = parser.parse_args()

    print(f"Searching for {args.trade}s near {args.location} (radius: {args.radius}km)...")

    s, w, n, e = geocode(args.location)
    s, w, n, e = expand_bbox(s, w, n, e, args.radius)

    print("Querying OpenStreetMap...")
    data = query_overpass(args.trade, s, w, n, e)
    leads = parse_results(data.get('elements', []))

    if not leads:
        print("No results found. Try a larger radius or different trade.")
        sys.exit(0)

    filename = save_csv(leads, args.trade, args.location)

    print(f"\nFound {len(leads)} {args.trade}s:")
    for l in leads:
        contact = l['phone'] or l['mobile'] or l['email'] or l['website'] or 'no contact info'
        print(f"  - {l['name']} | {contact}")

    print(f"\nSaved to: {filename}")


if __name__ == '__main__':
    main()
