#!/usr/bin/env python3
"""
GBP Report - Generate a monthly AI visibility + review report for a client.

Usage:
  python3 gbp-report.py --client j-shipley
"""

import argparse
import json
import os
import sys
from datetime import datetime

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES      = ['https://www.googleapis.com/auth/business.manage']
SCRIPTS_DIR = os.path.dirname(__file__)
CLIENTS_DIR = os.path.join(SCRIPTS_DIR, '..', 'clients')


def client_dir(slug):   return os.path.join(CLIENTS_DIR, slug)
def token_path(slug):   return os.path.join(client_dir(slug), 'gbp-token.json')
def config_path(slug):  return os.path.join(client_dir(slug), 'config.json')
def reports_dir(slug):
    d = os.path.join(client_dir(slug), 'reports')
    os.makedirs(d, exist_ok=True)
    return d


def get_creds(slug):
    creds = Credentials.from_authorized_user_file(token_path(slug), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path(slug), 'w') as f:
            f.write(creds.to_json())
    return creds


def get_config(slug):
    with open(config_path(slug)) as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--client', required=True)
    args = parser.parse_args()

    slug   = args.client
    config = get_config(slug)
    creds  = get_creds(slug)

    business_name = config.get('gbp_name') or config.get('name')
    location_id   = config.get('location_id')
    trade         = config.get('trade', 'trades business')

    import googleapiclient.discovery
    review_service = googleapiclient.discovery.build(
        'mybusiness', 'v4',
        credentials=creds,
        discoveryServiceUrl='https://mybusiness.googleapis.com/$discovery/rest'
    )

    # Fetch reviews
    reviews = []
    page_token = None
    while True:
        kwargs = {'parent': location_id, 'pageSize': 50}
        if page_token:
            kwargs['pageToken'] = page_token
        resp = review_service.locations().reviews().list(**kwargs).execute()
        reviews.extend(resp.get('reviews', []))
        page_token = resp.get('nextPageToken')
        if not page_token:
            break

    total    = len(reviews)
    replied  = sum(1 for r in reviews if r.get('reviewReply'))
    stars    = [{'ONE':1,'TWO':2,'THREE':3,'FOUR':4,'FIVE':5}.get(r.get('starRating','FIVE'),5) for r in reviews]
    avg      = round(sum(stars)/len(stars), 1) if stars else 0

    month = datetime.now().strftime('%B %Y')
    date  = datetime.now().strftime('%Y-%m-%d')

    report = f"""GeoXperts Monthly Report — {business_name}
{month}
{'='*50}

GOOGLE BUSINESS PROFILE
-----------------------
Total reviews:     {total}
Average rating:    {avg} / 5.0
Replies posted:    {replied} / {total}

"""

    # Recent reviews summary
    recent = sorted(reviews, key=lambda r: r.get('createTime',''), reverse=True)[:5]
    if recent:
        report += "RECENT REVIEWS\n--------------\n"
        for r in recent:
            stars_n = {'ONE':1,'TWO':2,'THREE':3,'FOUR':4,'FIVE':5}.get(r.get('starRating','FIVE'),5)
            name    = r.get('reviewer',{}).get('displayName','Anonymous')
            text    = r.get('comment','[no text]')[:100]
            rep     = '✓ replied' if r.get('reviewReply') else '— NO REPLY'
            report += f"  {'⭐'*stars_n} {name} ({rep})\n"
            report += f"  \"{text}\"\n\n"

    report += f"""AI VISIBILITY
-------------
[Manual check required — search the following in ChatGPT and Google AI:]

  "best {trade} in [area]"
  "{trade} near me [area]"
  "recommended {trade} [area]"

Screenshot results and note whether {business_name} appears.

NEXT STEPS
----------
- [ ] Respond to any un-replied reviews (run: gbp-reviews.py --client {slug} --post)
- [ ] Upload new geotagged photos of recent work
- [ ] Check NAP consistency across directories
- [ ] Review request messages sent this month: [fill in]

---
Report generated: {date}
GeoXperts — growth@geoXperts.co.uk
"""

    filename = os.path.join(reports_dir(slug), f"{date}-monthly-report.txt")
    with open(filename, 'w') as f:
        f.write(report)

    print(report)
    print(f"✓ Saved to: {filename}")


if __name__ == '__main__':
    main()
