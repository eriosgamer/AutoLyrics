# Lyrics

A desktop lyrics viewer for Linux that automatically detects the currently playing song and displays its lyrics in real time. Supports both MPRIS-compatible players and YouTube tabs in Firefox. Japanese lyrics are transliterated to romaji automatically.

## Features

- **Auto-detection** — detects the current song via MPRIS (`playerctl`) or Firefox window title (Hyprland)
- **Lyrics chain** — tries `lyrics.ovh` first, falls back to Genius scraping
- **Japanese transliteration** — converts hiragana/katakana/kanji to Hepburn romaji via `pykakasi`
- **Manual search** — search by artist/title when auto-detection isn't enough
- **Always on top** — toggle pin to keep the window above others
- **Copy to clipboard** — one-click copy of displayed lyrics
- **Dark theme** — Catppuccin Mocha-inspired UI

## Dependencies

### System

| Package | Purpose |
|---|---|
| `playerctl` | MPRIS metadata from media players |
| `hyprctl` | Window title fallback (Hyprland / Wayland) |
| `python3` | Runtime |
| Firefox | YouTube tab detection (via window title) |

### Python (in project venv)

| Package | Purpose |
|---|---|
| `PyQt5` | GUI framework |
| `requests` | HTTP client for lyrics APIs |
| `beautifulsoup4` + `lxml` | HTML scraping (Genius) |
| `pykakasi` | Japanese → romaji transliteration |
| `python-dotenv` | `.env` file loading |

## Setup

```bash
# 1. Clone the repository
git clone <repo-url> && cd lyrics

# 2. Create and activate the virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Configure Genius access token (optional)
cp .env.example .env
# Edit .env and paste your token: https://genius.com/api-clients

# 5. Run
python3 main.py
```

> **Note:** If you're on Arch Linux (or a distro with PEP 668), the venv is required because `pip install` will be blocked system-wide. The project includes a `sitecustomize.py` that automatically adds the venv site-packages to `sys.path` so you don't need to activate the venv manually — just run `python3 main.py` from the project root.

## Usage

- Launch with `python3 main.py`
- Play a song in any MPRIS-compatible player (Spotify, VLC, etc.) or a YouTube video in Firefox
- The window updates automatically every 2 seconds
- Use the search bar at the bottom for manual lookups
- Click the pin button to toggle always-on-top
- Click the copy button to copy lyrics to the clipboard

### No player detected?

The app will look for a Firefox window with a YouTube tab open and parse its title to extract artist/song. This is the fallback when MPRIS metadata is frozen (common with Firefox).

## Architecture

```
MPRIS (playerctl)  ────┐
                        ├──> best song data ──> lyrics_api.py ──> UI
Firefox window title  ─┘       │
                                ├── lyrics.ovh (primary, no auth)
                                ├── Genius (fallback, scraping)
                                └── transliterate (Japanese → romaji)
```

- `main.py` — entry point, QApplication setup, `load_dotenv()`
- `mpris.py` — wraps `playerctl metadata`, cleans YouTube noise from titles
- `window_title.py` — reads Firefox window titles via `hyprctl clients -j`
- `lyrics_api.py` — chain: `lyrics.ovh` → Genius → transliteration
- `genius.py` — search `genius.com/api/search/song`, scrape `div[data-lyrics-container]`
- `transliterate.py` — detect Japanese chars, convert to Hepburn romaji
- `ui.py` — PyQt5 GUI, auto-poll timer, manual search, pin/copy controls

## License

MIT
