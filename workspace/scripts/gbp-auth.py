#!/usr/bin/env python3
"""
GBP Auth - Authorise a client's Google Business Profile for management.
Run once per client. Opens browser for Google OAuth, stores token.

Usage:
  python3 gbp-auth.py --client "j-shipley" --name "J Shipley & Co."
  python3 gbp-auth.py --list
"""

import argparse
import json
import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    'https://www.googleapis.com/auth/business.manage',
]

SCRIPTS_DIR  = os.path.dirname(__file__)
CLIENTS_DIR  = os.path.join(SCRIPTS_DIR, '..', 'clients')
CREDS_FILE   = os.path.join(SCRIPTS_DIR, '..', 'config', 'gbp-oauth-credentials.json')


def client_dir(slug):
    return os.path.join(CLIENTS_DIR, slug)


def token_path(slug):
    return os.path.join(client_dir(slug), 'gbp-token.json')


def config_path(slug):
    return os.path.join(client_dir(slug), 'config.json')


def authorise(slug, name):
    if not os.path.exists(CREDS_FILE):
        print(f"ERROR: OAuth credentials file not found at:\n  {CREDS_FILE}")
        print("\nDownload it from Google Cloud Console → APIs & Services → Credentials")
        print("and save it to that path.")
        sys.exit(1)

    os.makedirs(client_dir(slug), exist_ok=True)

    creds = None
    if os.path.exists(token_path(slug)):
        creds = Credentials.from_authorized_user_file(token_path(slug), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing existing token...")
            creds.refresh(Request())
        else:
            print(f"Opening browser to authorise {name}...")
            print("Ask the client to log into their Google account and click Allow.")
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=8080)

        with open(token_path(slug), 'w') as f:
            f.write(creds.to_json())
        print(f"✓ Token saved: {token_path(slug)}")

    # Save/update client config
    config = {}
    if os.path.exists(config_path(slug)):
        with open(config_path(slug)) as f:
            config = json.load(f)

    config.update({'slug': slug, 'name': name})
    with open(config_path(slug), 'w') as f:
        json.dump(config, f, indent=2)

    print(f"✓ Client '{name}' authorised and ready.")
    print(f"\nNext: run gbp-setup.py --client {slug} to find their GBP account and location IDs.")


def list_clients():
    if not os.path.exists(CLIENTS_DIR):
        print("No clients yet.")
        return
    for slug in sorted(os.listdir(CLIENTS_DIR)):
        cfg = config_path(slug)
        tok = token_path(slug)
        if os.path.exists(cfg):
            with open(cfg) as f:
                c = json.load(f)
            authorised = "✓" if os.path.exists(tok) else "✗"
            account_id = c.get('account_id', 'not set up')
            print(f"  {authorised} {slug:30} | {c.get('name', '')} | account: {account_id}")


def main():
    parser = argparse.ArgumentParser(description='Authorise a client GBP account')
    parser.add_argument('--client', help='Client slug (e.g. j-shipley)')
    parser.add_argument('--name',   help='Client display name (e.g. "J Shipley & Co.")')
    parser.add_argument('--list',   action='store_true', help='List all clients')
    args = parser.parse_args()

    if args.list:
        list_clients()
    elif args.client and args.name:
        authorise(args.client, args.name)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
