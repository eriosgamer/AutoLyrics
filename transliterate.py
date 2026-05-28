import re
import logging

logger = logging.getLogger(__name__)

JAPANESE_RE = re.compile(r'[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\uff00-\uffef]')
EXTRA_SPACES = re.compile(r'\s{2,}')
SPACE_BEFORE_PUNCT = re.compile(r'\s+(?=[\]\)》、。！？?!])')

_kks = None


def _get_kakasi():
    global _kks
    if _kks is None:
        try:
            import pykakasi
            _kks = pykakasi.kakasi()
        except ImportError:
            logger.warning("pykakasi not installed, Japanese transliteration unavailable")
    return _kks


def has_japanese(text):
    return bool(JAPANESE_RE.search(text))


def to_romaji(text):
    if not text or not has_japanese(text):
        return text

    kks = _get_kakasi()
    if kks is None:
        return text

    try:
        result = kks.convert(text)
        spaced = ' '.join(item['hepburn'] for item in result)
        spaced = SPACE_BEFORE_PUNCT.sub('', spaced)
        spaced = EXTRA_SPACES.sub(' ', spaced).strip()
        return spaced
    except Exception as e:
        logger.warning(f"Transliteration failed: {e}")
        return text


def transliterate_lyrics(lyrics):
    if not lyrics or not has_japanese(lyrics):
        return lyrics, False

    lines = lyrics.split('\n')
    result = []
    for line in lines:
        if line.strip() and has_japanese(line.strip()):
            result.append(to_romaji(line))
        else:
            result.append(line)

    return '\n'.join(result), True
