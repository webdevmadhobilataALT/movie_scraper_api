

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

# ============================================================
# 🔥 MovieBox (moviebox.ph) এর জন্য সিলেক্টর
# নোট: ডিটেইল পেজের সিলেক্টরগুলো অনুমানভিত্তিক—আসল HTML পেলে আপডেট করব
# ============================================================
SELECTORS = {
    # হোমপেজ/ক্যাটাগরি পেজে মুভি লিংক
    'movie_link': 'a.movie-card[href^="/moviedetail/"]',
    
    # মুভি লিংকের ভেতর টাইটেল
    'title_in_list': 'p.w-full.text-white\\/80',
    
    # ডিটেইল পেজের জন্য (ডিফল্ট, পরবর্তীতে আপডেট হবে)
    'category_link': 'ul.categories li a, .menu-item a[href*="director"]',
    'title': 'h1.entry-title, h1.movie-title, h1',
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
# ============================================================


def fetch_html(url, timeout_ms=None):
    """Fetch HTML from a URL with custom headers and timeout."""
    if timeout_ms is None:
        timeout_ms = settings.REQUEST_TIMEOUT_MS / 1000.0
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout_ms)
        response.raise_for_status()
        time.sleep(1.5)
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


def extract_text(soup, selector, default='N/A'):
    """Extract clean text from the first CSS selector match."""
    element = soup.select_one(selector)
    return element.get_text(strip=True) if element else default


# ---------- CATEGORIES ----------
def get_categories(base_url):
    """
    Scrape the homepage and extract all category links.
    MovieBox-এর জন্য এটি কাজ নাও করতে পারে, কারণ সাইট ডায়নামিক।
    """
    html = fetch_html(base_url)
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
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

    categories = []
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


# ---------- MOVIE LIST (PAGINATED) ----------
def get_movie_list(category_url, page=1, max_items=None):
    """
    Fetch a paginated category page and extract movie summaries.
    MovieBox-এর জন্য পেজিনেশন: ?page=N অথবা /page/N/
    """
    if '?' in category_url:
        page_url = f"{category_url}&page={page}"
    else:
        page_url = f"{category_url}?page={page}"
    
    # Alternative pagination pattern
    page_url_alt = f"{category_url.rstrip('/')}/page/{page}/"

    html = fetch_html(page_url)
    if not html:
        html = fetch_html(page_url_alt)
        if not html:
            return []

    soup = BeautifulSoup(html, 'html.parser')
    
    # Try primary selector, fallback to generic
    movie_anchors = soup.select(SELECTORS['movie_link'])
    if not movie_anchors:
        movie_anchors = soup.select('a[href^="/moviedetail/"]')

    movies = []
    for a in movie_anchors:
        href = a.get('href')
        if not href:
            continue
        full_url = urljoin(settings.BASE_URL, href)
        
        # Extract title from the paragraph inside the card
        title_elem = a.select_one(SELECTORS['title_in_list'])
        title = title_elem.get_text(strip=True) if title_elem else 'Unknown'
        
        # Thumbnail (if any)
        thumbnail = None
        img = a.find('img')
        if img:
            thumbnail = img.get('src')

        movies.append({
            'title': title,
            'url': full_url,
            'thumbnail': thumbnail,
        })

        if max_items and len(movies) >= max_items:
            break

    return movies


# ---------- MOVIE DETAIL ----------
def get_movie_detail(movie_url):
    """
    Parse a single movie detail page.
    ⚠️ ডিটেইল পেজের HTML না পাওয়া পর্যন্ত এই ফাংশন কাজ করবে না।
    MovieBox-এর ডিটেইল পেজের HTML দিলে সঠিক সিলেক্টর আপডেট করে দেব।
    """
    html = fetch_html(movie_url)
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    # Extract u3m8 link (if present)
    u3m8_link = 'N/A'
    u3m8_elem = soup.select_one(SELECTORS['u3m8_selector'])
    if u3m8_elem:
        u3m8_link = (
            u3m8_elem.get('src') or 
            u3m8_elem.get('href') or 
            u3m8_elem.get('data-u3m8') or 
            u3m8_elem.get('data-link') or 
            'N/A'
        )

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
        'u3m8_link': u3m8_link,
    }

    if data['title'] == 'N/A':
        logger.warning(f"No title found for {movie_url}. Skipping.")
        return None

    return data


# ---------- SEARCH ----------
def search_movies(query, base_url):
    """
    Search for movies on MovieBox.
    MovieBox-এর সার্চ প্যাটার্ন অনুমানভিত্তিক, কাজ নাও করতে পারে।
    """
    search_urls = [
        f"{base_url}/search?q={query}",
        f"{base_url}/?s={query}",
        f"{base_url}/search/{query}",
    ]
    
    for search_url in search_urls:
        html = fetch_html(search_url)
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            movie_anchors = soup.select(SELECTORS['movie_link'])
            if not movie_anchors:
                movie_anchors = soup.select('a[href^="/moviedetail/"]')
            if movie_anchors:
                results = []
                for a in movie_anchors:
                    href = a.get('href')
                    if href:
                        full_url = urljoin(base_url, href)
                        title_elem = a.select_one(SELECTORS['title_in_list'])
                        title = title_elem.get_text(strip=True) if title_elem else 'Unknown'
                        results.append({'title': title, 'url': full_url})
                return results
    return []


# ---------- FULL CATEGORY SCRAPE ----------
def scrape_category_pages(base_url, start_path, max_pages=517, max_movies=None):
    """
    Scrape all pages of a category.
    """
    start_url = urljoin(base_url, start_path)
    all_movies = []
    page = 1
    total_fetched = 0

    while page <= max_pages:
        # Try both pagination patterns
        if '?' in start_url:
            page_url = f"{start_url}&page={page}"
        else:
            page_url = f"{start_url}?page={page}"
        
        page_url_alt = f"{start_url.rstrip('/')}/page/{page}/"

        logger.info(f"Scraping page {page}")
        html = fetch_html(page_url)
        if not html:
            html = fetch_html(page_url_alt)
            if not html:
                logger.warning(f"Page {page} failed. Stopping.")
                break

        soup = BeautifulSoup(html, 'html.parser')
        movie_anchors = soup.select(SELECTORS['movie_link'])
        if not movie_anchors:
            movie_anchors = soup.select('a[href^="/moviedetail/"]')

        if not movie_anchors:
            logger.info(f"No movies found on page {page}. Ending.")
            break

        for a in movie_anchors:
            href = a.get('href')
            if not href:
                continue
            movie_url = urljoin(base_url, href)
            movie_data = get_movie_detail(movie_url)

            if movie_data:
                all_movies.append(movie_data)
                total_fetched += 1
                logger.info(f"Fetched {total_fetched} movies so far")

                if max_movies and total_fetched >= max_movies:
                    return all_movies

        page += 1

    return all_movies

