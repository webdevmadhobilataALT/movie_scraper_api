

# scraper/utils.py
import requests
import time
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    'Referer': settings.REFERER,
    'Origin': settings.ORIGIN,
    'User-Agent': settings.USER_AGENT,
}

SELECTORS = {
    'category_link': 'ul.categories li a, .menu-item a[href*="director"], nav a[href*="/genre/"]',
    'movie_link': '.ml-item a, .post a, article a, div.item a',
    'title': 'h1, .entry-title, .post-title, .movie-title',
    'genre': '.genre, .mvi-genre, .cat-links',
    'director': '.director, .mvi-director',
    'actors': '.actors, .mvi-actors',
    'country': '.country, .mvi-country',
    'duration': '.duration, .mvi-duration',
    'quality': '.quality, .mvi-quality',
    'release': '.release, .mvi-release, .date',
    'imdb': '.imdb, .mvi-imdb',
    'description': '.description, .mvi-description, .entry-content p',
    'u3m8_selector': 'iframe[src*="u3m8"], a[href*="u3m8"], [data-u3m8], #player, .player-iframe',
}


def fetch_html(url, timeout_ms=None):
    if timeout_ms is None:
        timeout_ms = settings.REQUEST_TIMEOUT_MS / 1000.0
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout_ms)
        response.raise_for_status()
        time.sleep(1.5)
        return response.text
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


def extract_text(soup, selector, default='N/A'):
    elem = soup.select_one(selector)
    return elem.get_text(strip=True) if elem else default


def get_categories(base_url):
    """Scrape homepage and return list of categories."""
    html = fetch_html(base_url)
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    categories = []
    selectors_to_try = [
        'ul.categories li a',
        '.menu-item a[href*="director"]',
        'nav a[href*="/genre/"]',
        'nav a[href*="/director/"]',
        '.category-list a',
        '.cat-item a',
        'li a[href*="director"]',
        'li a[href*="genre"]',
    ]

    for selector in selectors_to_try:
        anchors = soup.select(selector)
        if anchors:
            for a in anchors:
                href = a.get('href')
                if href and not href.startswith('#') and len(href) > 1:
                    full_url = urljoin(base_url, href)
                    name = a.get_text(strip=True)
                    if name and full_url and len(name) > 1:
                        categories.append({'name': name, 'url': full_url})
            break

    # Remove duplicates
    seen = set()
    unique = []
    for cat in categories:
        if cat['url'] not in seen:
            seen.add(cat['url'])
            unique.append(cat)
    return unique

