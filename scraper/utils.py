

# scraper/utils.py
import requests
import time
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from django.conf import settings

logger = logging.getLogger(__name__)

# Default headers for all HTTP requests
DEFAULT_HEADERS = {
    'Referer': settings.REFERER,
    'Origin': settings.ORIGIN,
    'User-Agent': settings.USER_AGENT,
}

# CSS selectors for the target website (watchofree.website)
SELECTORS = {
    'category_link': 'ul.categories li a',      # Category links on homepage
    'movie_link': 'div.movie-item a',           # Movie links in listings
    'title': 'h1.movie-title',
    'genre': 'span.genre',
    'director': 'span.director',
    'actors': 'span.actors',
    'country': 'span.country',
    'duration': 'span.duration',
    'quality': 'span.quality',
    'release': 'span.release',
    'imdb': 'span.imdb',
    'description': 'div.description',
}


def fetch_html(url, timeout_ms=None):
    """
    Fetch HTML from a URL with custom headers and timeout.
    Returns HTML string or None on failure.
    """
    if timeout_ms is None:
        timeout_ms = settings.REQUEST_TIMEOUT_MS / 1000.0

    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout_ms)
        response.raise_for_status()
        time.sleep(1)  # Polite delay to avoid rate-limiting
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


def extract_text(soup, selector, default='N/A'):
    """Extract clean text from the first CSS selector match."""
    element = soup.select_one(selector)
    return element.get_text(strip=True) if element else default


def get_categories(base_url):
    """
    Scrape the homepage and extract all category links.
    Returns a list of dicts: [{'name': 'Hollywood', 'url': 'https://...'}, ...]
    """
    html = fetch_html(base_url)
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    category_anchors = soup.select(SELECTORS['category_link'])
    categories = []

    for anchor in category_anchors:
        href = anchor.get('href')
        if not href:
            continue
        full_url = urljoin(base_url, href)
        name = anchor.get_text(strip=True)
        if name and full_url:
            categories.append({'name': name, 'url': full_url})

    return categories


def get_movie_list(category_url, page=1, max_items=None):
    """
    Fetch a specific paginated category page and extract movie summaries.
    Returns a list of dicts: [{'title': '...', 'url': '...', 'thumbnail': '...'}, ...]
    """
    # Construct the paginated URL
    if '?' in category_url:
        page_url = f"{category_url}&page={page}"
    else:
        page_url = f"{category_url}?page={page}"

    html = fetch_html(page_url)
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    movie_anchors = soup.select(SELECTORS['movie_link'])
    movies = []

    for anchor in movie_anchors:
        href = anchor.get('href')
        if not href:
            continue
        full_url = urljoin(settings.BASE_URL, href)
        title = anchor.get_text(strip=True) or 'Unknown'

        # Extract thumbnail if available
        img = anchor.find('img')
        thumbnail = img.get('src') if img else None

        movies.append({
            'title': title,
            'url': full_url,
            'thumbnail': thumbnail,
        })

        if max_items and len(movies) >= max_items:
            break

    return movies


def get_movie_detail(movie_url):
    """
    Parse a single movie detail page and extract all 10 required fields.
    Returns a dict or None if the title is missing.
    """
    html = fetch_html(movie_url)
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    data = {
        'title': extract_text(soup, SELECTORS['title']),
        'genre': extract_text(soup, SELECTORS['genre']),
        'director': extract_text(soup, SELECTORS['director']),
        'actors': extract_text(soup, SELECTORS['actors']),
        'country': extract_text(soup, SELECTORS['country']),
        'duration': extract_text(soup, SELECTORS['duration']),
        'quality': extract_text(soup, SELECTORS['quality']),
        'release': extract_text(soup, SELECTORS['release']),
        'imdb': extract_text(soup, SELECTORS['imdb']),
        'description': extract_text(soup, SELECTORS['description']),
    }

    # Skip movies without a valid title
    if data['title'] == 'N/A':
        logger.warning(f"No title found for {movie_url}. Skipping.")
        return None

    return data


def search_movies(query, base_url):
    """
    Perform a search on the website.
    Adjusts the search URL pattern (currently assumes '/search?q=').
    Returns a list of movie summaries (same format as get_movie_list).
    """
    # Common search patterns - adjust if the site uses a different one
    search_url = f"{base_url}/search?q={query}"
    # Alternative pattern (uncomment if needed):
    # search_url = f"{base_url}/?s={query}"

    html = fetch_html(search_url)
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    movie_anchors = soup.select(SELECTORS['movie_link'])
    results = []

    for anchor in movie_anchors:
        href = anchor.get('href')
        if not href:
            continue
        full_url = urljoin(base_url, href)
        title = anchor.get_text(strip=True) or 'Unknown'
        results.append({'title': title, 'url': full_url})

    return results


def scrape_category_pages(base_url, start_path, max_pages=517, max_movies=None):
    """
    Full-scrape orchestrator: iterates through paginated pages (1 to max_pages),
    collects ALL movies, and returns a flat list of detailed movie dicts.
    Stops early if a page has no links or if max_movies is reached.
    """
    start_url = urljoin(base_url, start_path)
    all_movies = []
    page = 1
    total_fetched = 0

    while page <= max_pages:
        # Build paginated URL
        if '?' in start_url:
            page_url = f"{start_url}&page={page}"
        else:
            page_url = f"{start_url}?page={page}"

        logger.info(f"Scraping full category: page {page}")
        html = fetch_html(page_url)
        if not html:
            logger.warning(f"Page {page} returned no data. Stopping.")
            break

        soup = BeautifulSoup(html, 'html.parser')
        movie_anchors = soup.select(SELECTORS['movie_link'])

        if not movie_anchors:
            logger.info(f"No movies found on page {page}. Ending.")
            break

        for anchor in movie_anchors:
            href = anchor.get('href')
            if not href:
                continue
            movie_url = urljoin(base_url, href)
            movie_data = get_movie_detail(movie_url)

            if movie_data:
                all_movies.append(movie_data)
                total_fetched += 1

                # Stop if we've reached the max_movies limit
                if max_movies and total_fetched >= max_movies:
                    return all_movies

        page += 1

    return all_movies