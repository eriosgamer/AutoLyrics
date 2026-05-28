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
    if not _check_hyprctl():
        return None

    try:
        result = subprocess.run(
            ['hyprctl', 'clients', '-j'],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode != 0:
            return None

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
                    return clean, visible
    except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.debug(f"hyprctl error: {e}")

    return None


TITLE_SPLIT = re.compile(r'\s*[-–—]\s+')


def parse_window_title(title):
    if not title:
        return None, None

    song = title.strip()
    artist = ''

    parts = TITLE_SPLIT.split(song, maxsplit=1)
    if len(parts) == 2:
        artist = parts[0].strip()
        song = parts[1].strip()

    if song:
        song = re.sub(r'\s*\(Music Video\)\s*$', '', song, flags=re.IGNORECASE)
        song = re.sub(r'\s*\(Official Video\)\s*$', '', song, flags=re.IGNORECASE)
        song = re.sub(r'\s*\(Official Music Video\)\s*$', '', song, flags=re.IGNORECASE)
        song = re.sub(r'\s*\(Lyrics?\)\s*$', '', song, flags=re.IGNORECASE)
        song = re.sub(r'\s*\(Audio\)\s*$', '', song, flags=re.IGNORECASE)
        song = re.sub(r'\s*[([{]?\s*feat\.?\s+.*?[\])}]?\s*$', '', song, flags=re.IGNORECASE)
        song = re.sub(r'\s*[([{]?\s*ft\.?\s+.*?[\])}]?\s*$', '', song, flags=re.IGNORECASE)
        song = song.strip()

    return song, artist
