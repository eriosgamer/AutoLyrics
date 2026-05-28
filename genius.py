import os
import requests
import re
import logging
from urllib.parse import quote
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

ACCESS_TOKEN = os.getenv('GENIUS_ACCESS_TOKEN', '')

API_HEADERS = None
if ACCESS_TOKEN:
    API_HEADERS = {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
    }

SCRAPE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

SEARCH_URL = 'https://genius.com/api/search/song?q={query}'


def _search_song(artist, title, query_str=None):
    if query_str is None:
        query_str = f"{artist} {title}" if artist else title
    query = quote(query_str)
    url = SEARCH_URL.format(query=query)

    try:
        resp = requests.get(url, headers=SCRAPE_HEADERS, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"Genius search returned {resp.status_code}")
            return None

        data = resp.json()
        hits = data.get('response', {}).get('sections', [])
        songs = []
        for section in hits:
            if section.get('type') == 'song':
                for hit in section.get('hits', []):
                    result = hit.get('result', {})
                    songs.append({
                        'title': result.get('title'),
                        'artist': result.get('primary_artist', {}).get('name'),
                        'url': result.get('url'),
                        'id': result.get('id'),
                        'artist_id': result.get('primary_artist', {}).get('id'),
                    })

        if not songs:
            return None

        _prefer_original(songs, artist)
        return songs[0]

    except requests.RequestException as e:
        logger.warning(f"Genius search failed: {e}")
    except ValueError:
        logger.warning("Genius search returned invalid JSON")

    return None


def _prefer_original(songs, artist):
    tag_penalty = {'english translation': 3, 'romanized': 2}

    def score(s):
        title_lower = (s['title'] or '').lower()
        artist_lower = (s['artist'] or '').lower()
        penalty = 0
        for keyword, p in tag_penalty.items():
            if keyword in title_lower:
                penalty += p
        if artist_lower not in ('genius english translations', 'genius romanizations'):
            penalty -= 1
        return penalty

    songs.sort(key=score)


def _scrape_lyrics(song_url):
    try:
        resp = requests.get(song_url, headers=SCRAPE_HEADERS, timeout=10)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, 'lxml')
        containers = soup.select('div[data-lyrics-container="true"]')

        if not containers:
            return None

        parts = []
        for c in containers:
            text = c.get_text('\n').strip()
            if text:
                parts.append(text)

        if not parts:
            return None

        full = '\n\n'.join(parts)
        return _clean_lyrics(full.strip())

    except requests.RequestException as e:
        logger.warning(f"Genius scrape failed: {e}")
    except Exception as e:
        logger.warning(f"Genius parse error: {e}")

    return None


def _clean_lyrics(text):
    lines = text.split('\n')
    cleaned = []
    skip_patterns = [
        'Contributors', 'Lyrics', 'Embed', 'About',
        'You might also like', 'See the latest',
        'Translations', 'English', 'Romanization',
    ]
    skip_partial = [re.compile(r'^\d+\s+Contributors?')]
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned.append('')
            continue
        skip = False
        for pattern in skip_patterns:
            if stripped.startswith(pattern):
                skip = True
                break
        for regex in skip_partial:
            if regex.match(stripped):
                skip = True
                break
        if not skip:
            cleaned.append(stripped)

    return '\n'.join(cleaned).strip()


def fetch_lyrics(artist, title):
    if not title:
        return None

    song = _search_song(artist, title)
    if not song and title:
        # Artist may not match (e.g. YouTube alias vs Genius artist),
        # try title-only search as fallback
        logger.debug(f"Genius: retrying with title-only for {title}")
        song = _search_song(artist, title, query_str=title)

    if not song or not song.get('url'):
        logger.debug(f"Genius: no song found for {artist} - {title}")
        return None

    logger.debug(f"Genius: found {song['artist']} - {song['title']} at {song['url']}")
    lyrics = _scrape_lyrics(song['url'])

    if lyrics:
        logger.debug(f"Genius: got {len(lyrics)} chars")
        return lyrics

    return None
