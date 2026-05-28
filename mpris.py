import subprocess
import re
import logging
import shlex

logger = logging.getLogger(__name__)

YT_NOISE_PATTERNS = [
    (re.compile(r'\s*\(Official\s+(?:Music\s+)?Video\)\s*$', re.IGNORECASE), ''),
    (re.compile(r'\s*\(Official\s+Lyric\s+Video\)\s*$', re.IGNORECASE), ''),
    (re.compile(r'\s*\(Lyrics?\)\s*$', re.IGNORECASE), ''),
    (re.compile(r'\s*\(Audio\)\s*$', re.IGNORECASE), ''),
    (re.compile(r'\s*\(Video\)\s*$', re.IGNORECASE), ''),
    (re.compile(r'\s*\(Visualizer\)\s*$', re.IGNORECASE), ''),
    (re.compile(r'\s*\([^)]*Version\)\s*$', re.IGNORECASE), ''),
    (re.compile(r'\s*\(4K.*?\)\s*$', re.IGNORECASE), ''),
    (re.compile(r'\s*\[.*?\]\s*$'), ''),
    (re.compile(r'\s*\(feat\..*?\)\s*$', re.IGNORECASE), ''),
    (re.compile(r'\s*\(Ft\..*?\)\s*$', re.IGNORECASE), ''),
]

NOTHING_PLAYING_INDICATORS = [
    'nothing', 'not playing', '', 'stopped', 'paused',
]


def get_current_song():
    try:
        result = subprocess.run(
            ['playerctl', 'metadata', '--format',
             '{{title}}||{{artist}}||{{album}}||{{status}}||{{playerName}}'],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split('||')
            return {
                'title': parts[0].strip() if len(parts) > 0 else '',
                'artist': parts[1].strip() if len(parts) > 1 else '',
                'album': parts[2].strip() if len(parts) > 2 else '',
                'status': parts[3].strip() if len(parts) > 3 else '',
                'player': parts[4].strip() if len(parts) > 4 else '',
            }
    except FileNotFoundError:
        logger.error("playerctl not found — is it installed?")
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        logger.debug(f"playerctl error: {e}")
    return None


def clean_title(title):
    if not title:
        return title
    cleaned = title
    for pattern, replacement in YT_NOISE_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned.strip()


def parse_artist_title(data):
    title = data.get('title', '') if data else ''
    artist = data.get('artist', '') if data else ''

    if not title:
        return None, None

    raw_title = title
    title = clean_title(title)

    if artist and title.lower().startswith(artist.lower() + ' - '):
        title = title[len(artist) + 3:].strip()

    if not artist and ' - ' in title:
        parts = title.split(' - ', 1)
        artist = parts[0].strip()
        title = parts[1].strip()

    if not artist and ' - ' in raw_title:
        parts = raw_title.split(' - ', 1)
        artist = parts[0].strip()
        title = clean_title(parts[1].strip())

    if artist and artist.lower() in NOTHING_PLAYING_INDICATORS:
        artist = ''

    return title, artist


def is_playing(data):
    return data and data.get('status', '').lower() == 'playing'
