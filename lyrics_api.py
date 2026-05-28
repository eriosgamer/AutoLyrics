import logging
from urllib.parse import quote

import requests

import genius
from transliterate import transliterate_lyrics

logger = logging.getLogger(__name__)

LYRICS_OVH = 'https://api.lyrics.ovh/v1/{artist}/{title}'


def fetch_lyrics(artist, title):
    if not title:
        return None, False, None

    lyrics = _fetch_lyrics_ovh(artist, title)
    source = 'lyrics.ovh'

    if not lyrics:
        lyrics = genius.fetch_lyrics(artist, title)
        source = 'Genius'

    if not lyrics:
        return None, False, None

    display, was_transliterated = transliterate_lyrics(lyrics)
    return display, was_transliterated, source


def _fetch_lyrics_ovh(artist, title):
    artist_clean = quote(artist.strip()) if artist and artist.strip() else 'Unknown'
    title_clean = quote(title.strip())

    url = LYRICS_OVH.format(artist=artist_clean, title=title_clean)

    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            lyrics = data.get('lyrics', '')
            if lyrics:
                return lyrics.strip()
        elif resp.status_code == 404:
            logger.debug(f"lyrics.ovh: not found for {artist} - {title}")
        else:
            logger.debug(f"lyrics.ovh: returned {resp.status_code} for {url}")
    except requests.RequestException as e:
        logger.debug(f"lyrics.ovh: request failed: {e}")

    return None
