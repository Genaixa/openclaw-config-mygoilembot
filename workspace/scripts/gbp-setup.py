#!/usr/bin/env python3
"""
GBP Setup - Find and save a client's GBP account ID and location ID.
Run once after gbp-auth.py.

Usage:
  python3 gbp-setup.py --client "j-shipley"
"""

import argparse
import json
import os
import sys

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

SCOPES      = ['https://www.googleapis.com/auth/business.manage']
SCRIPTS_DIR = os.path.dirname(__file__)
CLIENTS_DIR = os.path.join(SCRIPTS_DIR, '..', 'clients')


def client_dir(slug):
    return os.path.join(CLIENTS_DIR, slug)

def token_path(slug):
    return os.path.join(client_dir(slug), 'gbp-token.json')

def config_path(slug):
    return os.path.join(client_dir(slug), 'config.json')

def get_creds(slug):
    if not os.path.exists(token_path(slug)):
        print(f"ERROR: No token for '{slug}'. Run gbp-auth.py --client {slug} first.")
        sys.exit(1)
    return Credentials.from_authorized_user_file(token_path(slug), SCOPES)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--client', required=True)
    args = parser.parse_args()
    slug = args.client

    creds = get_creds(slug)

    # List accounts
    acct_service = build('mybusinessaccountmanagement', 'v1', credentials=creds)
    accounts = acct_service.accounts().list().execute().get('accounts', [])

    if not accounts:
        print("No GBP accounts found for this Google account.")
        sys.exit(1)

    print(f"\nFound {len(accounts)} account(s):\n")
    for i, a in enumerate(accounts):
        print(f"  [{i}] {a['name']} — {a.get('accountName', '')} ({a.get('type', '')})")

    idx = 0
    if len(accounts) > 1:
        idx = int(input("\nWhich account? Enter number: "))

    account = accounts[idx]
    account_id = account['name']  # e.g. "accounts/123456"
    print(f"\n✓ Using account: {account.get('accountName')} ({account_id})")

    # List locations
    info_service = build('mybusinessbusinessinformation', 'v1', credentials=creds)
    locations = info_service.accounts().locations().list(
        parent=account_id,
        readMask='name,title,storefrontAddress'
    ).execute().get('locations', [])

    if not locations:
        print("No locations found under this account.")
        sys.exit(1)

    print(f"\nFound {len(locations)} location(s):\n")
    for i, l in enumerate(locations):
        addr = l.get('storefrontAddress', {})
        city = addr.get('locality', '')
        print(f"  [{i}] {l.get('title', '')} — {city} ({l['name']})")

    lidx = 0
    if len(locations) > 1:
        lidx = int(input("\nWhich location? Enter number: "))

    location = locations[lidx]
    location_id = location['name']  # e.g. "locations/789"
    print(f"\n✓ Using location: {location.get('title')} ({location_id})")

    # Save to config
    with open(config_path(slug)) as f:
        config = json.load(f)

    config['account_id']  = account_id
    config['location_id'] = location_id
    config['gbp_name']    = location.get('title', '')

    with open(config_path(slug), 'w') as f:
        json.dump(config, f, indent=2)

    print(f"\n✓ Config saved. Client '{slug}' is fully set up.")
    print(f"\nNow you can run:")
    print(f"  python3 gbp-reviews.py --client {slug}")


if __name__ == '__main__':
    main()
