import subprocess
import json
import re
import logging

logger = logging.getLogger(__name__)

YOUTUBE_SUFFIX = re.compile(
    r'\s*-\s*YouTube\s*—\s*Mozilla Firefox\s*$', re.IGNORECASE
)

YOUTUBE_SUFFIX_ALT = re.compile(
    r'\s*[-–—]\s*YouTube\s*[-–—]\s*Mozilla Firefox\s*$', re.IGNORECASE
)

HYPRCTL_READY = None
_last_youtube = None


def _check_hyprctl():
    global HYPRCTL_READY
    if HYPRCTL_READY is None:
        try:
            result = subprocess.run(
                ['hyprctl', 'clients', '-j'],
                capture_output=True, text=True, timeout=2
            )
            HYPRCTL_READY = result.returncode == 0
        except FileNotFoundError:
            HYPRCTL_READY = False
    return HYPRCTL_READY


def get_youtube_window_title():
    global _last_youtube
    if not _check_hyprctl():
        return None

    try:
        result = subprocess.run(
            ['hyprctl', 'clients', '-j'],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode != 0:
            return _last_youtube

        windows = json.loads(result.stdout)
        for w in windows:
            cls = w.get('class', '').lower()
            title = w.get('title', '')
            visible = w.get('visible', False)
            if 'firefox' in cls and 'youtube' in title.lower():
                clean = YOUTUBE_SUFFIX.sub('', title)
                clean = YOUTUBE_SUFFIX_ALT.sub('', clean)
                clean = clean.strip()
                if clean and clean.lower() != 'youtube':
                    logger.debug(f"YouTube tab: {clean} (visible={visible})")
                    _last_youtube = (clean, visible)
                    return _last_youtube

    except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.debug(f"hyprctl error: {e}")

    return _last_youtube


TITLE_SPLIT = re.compile(r'\s*[-–—]\s+')
JAPANESE_SONG = re.compile(r'「([^」]+)」')
JAPANESE_PREFIX = re.compile(r'^.*?』')
METADATA_BRACKETS = re.compile(r'【[^】]+】')


def parse_window_title(title):
    if not title:
        return None, None

    raw = title.replace('\xa0', ' ').strip()
    artist = ''
    song = ''

    # Strip common suffix first
    cleaned = METADATA_BRACKETS.sub('', raw).strip()

    # Try Japanese bracket format: ...HAYASii「Hunting Soul」
    song_match = JAPANESE_SONG.search(cleaned)
    if song_match:
        song = song_match.group(1).strip()
        # Everything before the 「...」 bracket (after stripping anime prefix) is the artist
        before = cleaned[:song_match.start()].strip()
        before = JAPANESE_PREFIX.sub('', before).strip()
        if before:
            # Remove leading punctuation/whitespace
            before = re.sub(r'^[\s\W]+', '', before).strip()
            if before:
                artist = before
        elif not artist:
            artist = ''
        if not song:
            song = ''
        return song, artist

    # Standard format: Artist - Title
    parts = TITLE_SPLIT.split(cleaned, maxsplit=1)
    if len(parts) == 2:
        artist = parts[0].strip()
        song = parts[1].strip()
    else:
        song = cleaned

    if song:
        song = re.sub(r'\s*\(Music Video\)\s*$', '', song, flags=re.IGNORECASE)
        song = re.sub(r'\s*\(Official Video\)\s*$', '', song, flags=re.IGNORECASE)
        song = re.sub(r'\s*\(Official Music Video\)\s*$', '', song, flags=re.IGNORECASE)
        song = re.sub(r'\s*\(Lyric Video\)\s*$', '', song, flags=re.IGNORECASE)
        song = re.sub(r'\s*\(Lyrics?\)\s*$', '', song, flags=re.IGNORECASE)
        song = re.sub(r'\s*\(Audio\)\s*$', '', song, flags=re.IGNORECASE)
        song = re.sub(r'\s*\[OFFICIAL VIDEO\]\s*$', '', song, flags=re.IGNORECASE)
        song = re.sub(r'\s*\[OFFICIAL MUSIC VIDEO\]\s*$', '', song, flags=re.IGNORECASE)
        song = re.sub(r'\s*\[Lyric Video\]\s*$', '', song, flags=re.IGNORECASE)
        song = re.sub(r'\s*\[Lyrics\]\s*$', '', song, flags=re.IGNORECASE)
        song = re.sub(r'\s*\[Audio\]\s*$', '', song, flags=re.IGNORECASE)
        song = re.sub(r'\s*[([{]?\s*feat\.?\s+.*?[\])}]?\s*$', '', song, flags=re.IGNORECASE)
        song = re.sub(r'\s*[([{]?\s*ft\.?\s+.*?[\])}]?\s*$', '', song, flags=re.IGNORECASE)
        song = re.sub(r'\s*[-–—]\s*$', '', song)
        song = song.strip()

    if artist:
        # Keep only first artist in collaborations (A / B, A x B, A vs B)
        artist = re.sub(r'\s*[/×x]\s*.*$', '', artist).strip()

    return song, artist
