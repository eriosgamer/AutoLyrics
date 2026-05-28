#!/usr/bin/env python3
import sys
import site
import os
import logging

# Bootstrap: add project venv site-packages before any project imports
_venv = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.venv')
_sp = os.path.join(_venv, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')
if os.path.isdir(_sp):
    site.addsitedir(_sp)

from dotenv import load_dotenv
load_dotenv()

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

import mpris
import lyrics_api
from ui import LyricsWindow

logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s | %(name)s | %(message)s',
)

logger = logging.getLogger('main')
logger.setLevel(logging.DEBUG)


class ModuleDetector:
    @staticmethod
    def get_current_song():
        return mpris.get_current_song()

    @staticmethod
    def parse_artist_title(data):
        return mpris.parse_artist_title(data)

    @staticmethod
    def is_playing(data):
        return mpris.is_playing(data)


class ModuleFetcher:
    @staticmethod
    def fetch_lyrics(artist, title):
        return lyrics_api.fetch_lyrics(artist, title)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Lyrics")

    font = QFont("sans-serif", 10)
    app.setFont(font)

    window = LyricsWindow(
        detector=ModuleDetector(),
        fetcher=ModuleFetcher(),
    )
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
