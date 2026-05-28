import logging
import re

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QLineEdit, QFrame,
    QApplication,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from window_title import get_youtube_window_title, parse_window_title

logger = logging.getLogger(__name__)

PAGE_STYLE = """
    QMainWindow, QWidget {
        background-color: #1e1e2e;
        color: #cdd6f4;
    }
    QLabel#headerTitle {
        font-size: 16px;
        font-weight: bold;
        color: #cdd6f4;
        padding: 0;
    }
    QLabel#headerArtist {
        font-size: 13px;
        color: #a6adc8;
        padding: 0;
    }
    QLabel#headerStatus {
        font-size: 11px;
        color: #585b70;
        padding: 0;
    }
    QTextEdit {
        background-color: #181825;
        color: #cdd6f4;
        border: 1px solid #313244;
        border-radius: 8px;
        padding: 14px;
        font-size: 14px;
        selection-background-color: #45475a;
    }
    QPushButton {
        background-color: #313244;
        color: #cdd6f4;
        border: 1px solid #45475a;
        border-radius: 6px;
        padding: 5px 12px;
        font-size: 13px;
        min-height: 24px;
    }
    QPushButton:hover {
        background-color: #45475a;
        border: 1px solid #585b70;
    }
    QPushButton:pressed {
        background-color: #585b70;
    }
    QPushButton#pinBtn[active="true"] {
        background-color: #89b4fa;
        color: #1e1e2e;
        border: 1px solid #89b4fa;
    }
    QLineEdit {
        background-color: #313244;
        color: #cdd6f4;
        border: 1px solid #45475a;
        border-radius: 6px;
        padding: 5px 8px;
        font-size: 13px;
        min-height: 24px;
    }
    QLineEdit:focus {
        border: 1px solid #89b4fa;
    }
    QFrame#separator {
        color: #313244;
        max-height: 1px;
    }
"""


def _normalize(s):
    return re.sub(r'\W+', '', s).lower()


class LyricsWindow(QMainWindow):
    def __init__(self, detector, fetcher):
        super().__init__()
        self.detector = detector
        self.fetcher = fetcher
        self.last_song_key = None
        self._setup_ui()
        self._auto_search_on_start()
        self._setup_timer()

    def _setup_ui(self):
        self.setWindowTitle("AutoLyrics")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setMinimumSize(420, 250)
        self.resize(520, 520)
        self.setStyleSheet(PAGE_STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(8)

        self._build_header(layout)
        self._build_lyrics_area(layout)
        self._build_footer(layout)

    def _build_header(self, layout):
        self.title_label = QLabel("🎵  Waiting for music...")
        self.title_label.setObjectName("headerTitle")
        layout.addWidget(self.title_label)

        self.artist_label = QLabel("")
        self.artist_label.setObjectName("headerArtist")
        layout.addWidget(self.artist_label)

        self.status_label = QLabel("")
        self.status_label.setObjectName("headerStatus")
        layout.addWidget(self.status_label)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

    def _build_lyrics_area(self, layout):
        self.lyrics_text = QTextEdit()
        self.lyrics_text.setReadOnly(True)
        self.lyrics_text.setFont(QFont("monospace", 13))
        self.lyrics_text.setPlaceholderText("Lyrics will appear here automatically...")
        self.lyrics_text.setTabChangesFocus(True)
        layout.addWidget(self.lyrics_text, stretch=1)

    def _build_footer(self, layout):
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        footer = QHBoxLayout()
        footer.setSpacing(6)

        refresh_btn = QPushButton("⟳")
        refresh_btn.setToolTip("Refresh lyrics")
        refresh_btn.setFixedWidth(34)
        refresh_btn.clicked.connect(self._manual_refresh)
        footer.addWidget(refresh_btn)

        self.pin_btn = QPushButton("📌")
        self.pin_btn.setObjectName("pinBtn")
        self.pin_btn.setToolTip("Toggle always on top")
        self.pin_btn.setFixedWidth(34)
        self.pin_btn.setProperty("active", True)
        self.pin_btn.clicked.connect(self._toggle_pin)
        footer.addWidget(self.pin_btn)

        copy_btn = QPushButton("📋")
        copy_btn.setToolTip("Copy lyrics to clipboard")
        copy_btn.setFixedWidth(34)
        copy_btn.clicked.connect(self._copy_lyrics)
        footer.addWidget(copy_btn)

        footer.addStretch()

        self.artist_input = QLineEdit()
        self.artist_input.setPlaceholderText("Artist")
        self.artist_input.setFixedWidth(140)
        self.artist_input.returnPressed.connect(self._manual_search)
        footer.addWidget(self.artist_input)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Song title")
        self.title_input.setFixedWidth(200)
        self.title_input.returnPressed.connect(self._manual_search)
        footer.addWidget(self.title_input)

        search_btn = QPushButton("🔍  Search")
        search_btn.clicked.connect(self._manual_search)
        footer.addWidget(search_btn)

        layout.addLayout(footer)

    def _setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self._poll_player)
        self.timer.start(2000)

    def _get_best_song_data(self):
        data = self.detector.get_current_song()
        if not data:
            win_song, win_artist = self._get_window_title()
            if win_song:
                return win_song, win_artist, 'Firefox tab', True, '▶'
            return None, None, None, False, '🎵'

        mtitle, martist = self.detector.parse_artist_title(data)
        status = data.get('status', '').lower()
        player = data.get('player', '')
        playing = self.detector.is_playing(data)
        is_firefox = 'firefox' in (player or '').lower()

        win_song, win_artist, win_player = None, None, False
        win_raw = get_youtube_window_title()
        if win_raw:
            ws, wa = parse_window_title(win_raw[0])
            win_song, win_artist, win_player = ws, wa, True

        if mtitle and win_song:
            m_norm = _normalize(mtitle)
            w_norm = _normalize(win_song)
            match = m_norm == w_norm or m_norm in w_norm or w_norm in m_norm

            if is_firefox and not match:
                logger.info(f"Window title differs from MPRIS, using window: {win_artist} - {win_song}")
                return win_song, win_artist or martist, 'Firefox tab', True, '▶'

        if mtitle:
            tag = {'playing': '▶', 'paused': '⏸'}.get(status, '🎵')
            return mtitle, martist, f"{player}" if player else 'MPRIS', playing, tag

        if win_song:
            return win_song, win_artist, 'Firefox tab', True, '▶'

        return None, None, None, False, '🎵'

    def _get_window_title(self):
        win_raw = get_youtube_window_title()
        if not win_raw:
            return None, None
        return parse_window_title(win_raw[0])

    def _process_song_data(self):
        title, artist, source, should_fetch, status_tag = self._get_best_song_data()
        if not title:
            self.last_song_key = None
            return False

        song_key = f"{artist}|{title}"
        if song_key == self.last_song_key:
            return True

        self.last_song_key = song_key
        display = f"{status_tag}  {title}" if status_tag else f"🎵  {title}"
        self.title_label.setText(display)
        self.artist_label.setText(artist or '')
        self.status_label.setText(f"via {source}" if source else "")

        self.artist_input.setText(artist or '')
        self.title_input.setText(title or '')

        if should_fetch:
            self._fetch_and_display(title, artist)

        return True

    def _auto_search_on_start(self):
        self._process_song_data()

    def _poll_player(self):
        self._process_song_data()

    def _fetch_and_display(self, title, artist, source_tag=''):
        self.lyrics_text.setPlainText("Searching for lyrics...")
        QApplication.processEvents()

        lyrics, was_transliterated, source = self.fetcher.fetch_lyrics(artist, title)

        if lyrics:
            self.lyrics_text.setPlainText(lyrics)
            self.lyrics_text.moveCursor(self.lyrics_text.textCursor().Start)

            source_label = source or source_tag
            if was_transliterated:
                source_label = f"{source_label} (romaji)"
            self.status_label.setText(f"via {source_label}" if source_label else "")
        else:
            self.lyrics_text.setPlainText(
                "Lyrics not found for this song.\n\n"
                "Try a manual search with different artist/title."
            )

    def _manual_refresh(self):
        if self.last_song_key:
            parts = self.last_song_key.split('|', 1)
            artist = parts[0] if len(parts) > 0 else ''
            title = parts[1] if len(parts) > 1 else ''
            self._fetch_and_display(title, artist)

    def _manual_search(self):
        artist = self.artist_input.text().strip()
        title = self.title_input.text().strip()
        if not title:
            return
        self.last_song_key = f"{artist}|{title}"
        self.title_label.setText(f"🔍  {title}")
        self.artist_label.setText(artist or '')
        self._fetch_and_display(title, artist)

    def _toggle_pin(self):
        stays_on_top = self.windowFlags() & Qt.WindowStaysOnTopHint
        if stays_on_top:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.pin_btn.setProperty("active", False)
        else:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.pin_btn.setProperty("active", True)
        self.pin_btn.style().unpolish(self.pin_btn)
        self.pin_btn.style().polish(self.pin_btn)
        self.show()

    def _copy_lyrics(self):
        lyrics = self.lyrics_text.toPlainText()
        if lyrics and "not found" not in lyrics and "Searching" not in lyrics:
            QApplication.clipboard().setText(lyrics)
            self.status_label.setText("✓  Lyrics copied to clipboard")
            QTimer.singleShot(3000, self._restore_status)

    def _restore_status(self):
        _, _, source, _, _ = self._get_best_song_data()
        if source:
            self.status_label.setText(f"via {source}")
