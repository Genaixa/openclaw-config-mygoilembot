#!/usr/bin/env python3
"""
GBP Reviews - Fetch new reviews for a client, draft AI replies, optionally post them.

Usage:
  python3 gbp-reviews.py --client j-shipley            # fetch + draft replies
  python3 gbp-reviews.py --client j-shipley --post     # fetch + draft + post replies
  python3 gbp-reviews.py --client j-shipley --list     # just show recent reviews
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import anthropic
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES      = ['https://www.googleapis.com/auth/business.manage']
SCRIPTS_DIR = os.path.dirname(__file__)
CLIENTS_DIR = os.path.join(SCRIPTS_DIR, '..', 'clients')

STAR_LABELS = {
    'ONE': '⭐ (1 star)',
    'TWO': '⭐⭐ (2 stars)',
    'THREE': '⭐⭐⭐ (3 stars)',
    'FOUR': '⭐⭐⭐⭐ (4 stars)',
    'FIVE': '⭐⭐⭐⭐⭐ (5 stars)',
}


def client_dir(slug):
    return os.path.join(CLIENTS_DIR, slug)

def token_path(slug):
    return os.path.join(client_dir(slug), 'gbp-token.json')

def config_path(slug):
    return os.path.join(client_dir(slug), 'config.json')

def reviews_dir(slug):
    d = os.path.join(client_dir(slug), 'reviews')
    os.makedirs(d, exist_ok=True)
    return d


def get_creds(slug):
    if not os.path.exists(token_path(slug)):
        print(f"ERROR: No token for '{slug}'. Run gbp-auth.py --client {slug} first.")
        sys.exit(1)
    creds = Credentials.from_authorized_user_file(token_path(slug), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path(slug), 'w') as f:
            f.write(creds.to_json())
    return creds


def get_config(slug):
    if not os.path.exists(config_path(slug)):
        print(f"ERROR: No config for '{slug}'. Run gbp-setup.py --client {slug} first.")
        sys.exit(1)
    with open(config_path(slug)) as f:
        return json.load(f)


def fetch_reviews(service, location_id):
    """Fetch all reviews for a location."""
    reviews = []
    page_token = None
    while True:
        kwargs = {'parent': location_id, 'pageSize': 50}
        if page_token:
            kwargs['pageToken'] = page_token
        resp = service.locations().reviews().list(**kwargs).execute()
        reviews.extend(resp.get('reviews', []))
        page_token = resp.get('nextPageToken')
        if not page_token:
            break
    return reviews


def draft_reply(review, business_name, trade):
    """Use Claude to draft a reply to a review."""
    client = anthropic.Anthropic()

    rating = review.get('starRating', 'FIVE')
    reviewer = review.get('reviewer', {}).get('displayName', 'there')
    comment = review.get('comment', '').strip()
    stars = int({'ONE':1,'TWO':2,'THREE':3,'FOUR':4,'FIVE':5}.get(rating, 5))

    if stars >= 4:
        tone = "warm, grateful, and genuine. Don't be over the top. Keep it short — 2-3 sentences."
    elif stars == 3:
        tone = "appreciative but also acknowledging that we can do better. Offer to discuss offline."
    else:
        tone = "calm, professional, and empathetic. Acknowledge the concern, apologise briefly, invite them to contact us directly to resolve it. Do not get defensive."

    prompt = f"""Write a Google review reply for {business_name}, a local {trade} business.

Reviewer name: {reviewer}
Star rating: {stars}/5
Review text: "{comment if comment else '[No written review — just a star rating]'}"

Tone: {tone}

Rules:
- Sound like a real person, not a PR department
- Use the reviewer's first name if it's a real name (not initials or "A Google User")
- Don't mention the star rating
- Don't use phrases like "We appreciate your feedback" or "Thank you for taking the time"
- Max 60 words
- No hashtags, no emojis unless the review used them

Reply only with the response text, nothing else."""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()


def post_reply(service, location_id, review_name, reply_text):
    """Post a reply to a review."""
    service.locations().reviews().updateReply(
        name=review_name,
        body={'comment': reply_text}
    ).execute()


def load_seen_reviews(slug):
    path = os.path.join(reviews_dir(slug), 'seen.json')
    if os.path.exists(path):
        with open(path) as f:
            return set(json.load(f))
    return set()


def save_seen_reviews(slug, seen):
    path = os.path.join(reviews_dir(slug), 'seen.json')
    with open(path, 'w') as f:
        json.dump(list(seen), f)


def main():
    parser = argparse.ArgumentParser(description='Manage GBP reviews for a client')
    parser.add_argument('--client', required=True)
    parser.add_argument('--post',   action='store_true', help='Auto-post drafted replies')
    parser.add_argument('--list',   action='store_true', help='Just list reviews, no replies')
    parser.add_argument('--all',    action='store_true', help='Process all reviews, not just new ones')
    args = parser.parse_args()

    slug   = args.client
    config = get_config(slug)
    creds  = get_creds(slug)

    location_id   = config.get('location_id')
    business_name = config.get('gbp_name') or config.get('name')
    trade         = config.get('trade', 'trades')

    if not location_id:
        print("ERROR: No location_id in config. Run gbp-setup.py first.")
        sys.exit(1)

    # Use v4 API for reviews (Business Profile API)
    service = build('mybusiness', 'v4', credentials=creds,
                    discoveryServiceUrl='https://mybusinessbusinessinformation.googleapis.com/$discovery/rest?version=v1')

    # Actually use the correct review endpoint
    import googleapiclient.discovery
    review_service = googleapiclient.discovery.build(
        'mybusiness', 'v4',
        credentials=creds,
        discoveryServiceUrl='https://mybusiness.googleapis.com/$discovery/rest'
    )

    print(f"Fetching reviews for {business_name}...")
    reviews = fetch_reviews(review_service, location_id)
    print(f"Found {len(reviews)} review(s) total.\n")

    if args.list:
        for r in reviews:
            rating = STAR_LABELS.get(r.get('starRating',''), '')
            name   = r.get('reviewer', {}).get('displayName', 'Anonymous')
            text   = r.get('comment', '[no text]')[:100]
            replied = '✓ replied' if r.get('reviewReply') else '— no reply'
            print(f"  {rating} | {name} | {replied}")
            print(f"    \"{text}\"")
        return

    seen = load_seen_reviews(slug) if not args.all else set()
    new_reviews = [r for r in reviews if r['name'] not in seen and not r.get('reviewReply')]

    if not new_reviews:
        print("No new un-replied reviews.")
        return

    print(f"{len(new_reviews)} review(s) need a reply.\n")

    drafted = []
    for r in new_reviews:
        rating  = STAR_LABELS.get(r.get('starRating',''), '')
        name    = r.get('reviewer', {}).get('displayName', 'Anonymous')
        comment = r.get('comment', '[no text]')

        print(f"{rating} — {name}")
        print(f"  \"{comment[:120]}\"")
        print(f"  Drafting reply...")

        reply = draft_reply(r, business_name, trade)
        print(f"  Reply: \"{reply}\"")

        if args.post:
            post_reply(review_service, location_id, r['name'], reply)
            print(f"  ✓ Posted.")
        else:
            # Save draft locally
            date = datetime.now().strftime('%Y-%m-%d')
            draft_file = os.path.join(reviews_dir(slug), f"{date}-{r['name'].split('/')[-1]}.txt")
            with open(draft_file, 'w') as f:
                f.write(f"REVIEW: {rating} — {name}\n")
                f.write(f"TEXT: {comment}\n")
                f.write(f"{'—'*40}\n")
                f.write(f"REPLY:\n{reply}\n")
            print(f"  ✓ Draft saved: {draft_file}")

        drafted.append(r['name'])
        seen.add(r['name'])

    save_seen_reviews(slug, seen)

    print(f"\nDone. {len(drafted)} reply/replies {'posted' if args.post else 'drafted'}.")
    if not args.post:
        print("Run with --post to publish replies directly to Google.")


if __name__ == '__main__':
    main()
