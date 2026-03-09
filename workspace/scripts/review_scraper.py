#!/usr/bin/env python3
"""
Review Scraper - finds customer reviews/testimonials from a business website.
Returns the best review suitable for a personalised P.S. line.
"""

import re
import sys
import time
from html import unescape
from urllib.request import urlopen, Request
from urllib.parse import urljoin
from urllib.error import URLError

HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0'}

REVIEW_PATHS = [
    '/testimonials', '/reviews', '/feedback', '/what-our-customers-say',
    '/customer-reviews', '/about', '/about-us', '/our-customers',
]

POSITIVE_WORDS = [
    'recommend', 'excellent', 'great', 'professional', 'quick', 'friendly',
    'helpful', 'pleased', 'happy', 'fantastic', 'brilliant', 'superb',
    'reliable', 'efficient', 'prompt', 'outstanding', 'amazing', 'impressed',
    'quality', 'satisfied', 'first class', 'top notch', 'couldn\'t be happier',
]

NOISE = ['<!-- ', 'R-CONTENT', 'cookie', 'privacy', 'javascript', 'subscribe', 'newsletter']


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


def clean(text):
    text = unescape(text)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def score_review(text):
    """Score a review by how useful it is for a P.S. line."""
    # Filter out URLs and paths
    if text.startswith('http') or text.startswith('/') or '://' in text:
        return -99
    t = text.lower()
    score = 0
    for w in POSITIVE_WORDS:
        if w in t:
            score += 1
    # Penalise too short or too long
    if len(text) < 40:
        score -= 3
    if len(text) > 250:
        score -= 1
    # Penalise noise
    for n in NOISE:
        if n.lower() in t:
            score -= 10
    return score


def extract_reviews(html):
    reviews = []

    # Pattern 1: quoted strings (curly or straight quotes)
    for m in re.finditer(r'[\u201c\u2018\"](.*?)[\u201d\u2019\"]', html, re.DOTALL):
        text = clean(m.group(1))
        if 40 < len(text) < 350:
            reviews.append(text)

    # Pattern 2: testimonial/review divs
    for m in re.finditer(
        r'<(?:p|blockquote|div|span)[^>]*(?:review|testimonial|quote|feedback)[^>]*>(.*?)</(?:p|blockquote|div|span)>',
        html, re.IGNORECASE | re.DOTALL
    ):
        text = clean(m.group(1))
        if 40 < len(text) < 350:
            reviews.append(text)

    # Pattern 3: itemprop="reviewBody"
    for m in re.finditer(r'itemprop=["\']reviewBody["\'][^>]*>(.*?)<', html, re.DOTALL):
        text = clean(m.group(1))
        if 40 < len(text) < 350:
            reviews.append(text)

    return reviews


def find_best_review(website):
    """Scrape a website and return the best customer review found."""
    all_reviews = []

    # Scrape homepage + review pages
    pages = [''] + REVIEW_PATHS
    for path in pages:
        url = urljoin(website, path)
        html = fetch(url)
        if html:
            reviews = extract_reviews(html)
            all_reviews.extend(reviews)
        time.sleep(0.3)

    if not all_reviews:
        return None

    # Score and pick best
    scored = [(score_review(r), r) for r in all_reviews]
    scored.sort(reverse=True)

    # Return best if it has a positive score
    if scored[0][0] > 0:
        return scored[0][1][:220].rstrip('.,') + ('...' if len(scored[0][1]) > 220 else '')

    return None


if __name__ == '__main__':
    website = sys.argv[1] if len(sys.argv) > 1 else 'https://shipley-heating.co.uk'
    print(f"Scraping: {website}")
    review = find_best_review(website)
    if review:
        print(f"\nBest review found:\n\"{review}\"")
    else:
        print("No suitable review found.")
