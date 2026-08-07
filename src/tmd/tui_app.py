"""Textual TUI Application."""

import asyncio
import re
import numpy as np
from pathlib import Path
from typing import Optional, List

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, Container
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Header,
    Footer,
    Static,
    Input,
    DataTable,
    Button,
    Label,
    ProgressBar,
    ListView,
    ListItem,
    Markdown,
    RichLog,
)
from textual.canvas import Canvas

from tmd.database import Database, Song
from tmd.auth import is_authenticated, logout, Credentials, AuthenticationError
from tmd.sync import sync_liked_songs, SyncError
from tmd.download import DownloadManager, DownloadProgress
from tmd.search import search_youtube, add_to_liked_playlist
from tmd.player import AudioPlayer, PlaybackState, VisualizerData
from tmd.settings import Settings
from tmd.config import get_database_path, get_settings_path, get_music_dir


def _clean_msg(text: str) -> str:
    """Strip HTML and escape markup chars so Textual doesn't choke on error messages."""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Escape Textual markup brackets
    text = text.replace("[", "[[").replace("]", "]]")
    return text


# ── Visualizer Widget ──

class VisualizerWidget(Static):
    """Renders FFT frequency bars using Unicode blocks."""

    bars = reactive(np.zeros(32))
    peak = reactive(0.0)

    def __init__(self, num_bars: int = 32, **kwargs):
        super().__init__(**kwargs)
        self.num_bars = num_bars
        self._bar_chars = ["▏", "▎", "▍", "▌", "▋", "▊", "▉", "█"]
        self._colors = [
            "#00ff00",  # green
            "#80ff00",
            "#c0ff00",
            "#ffff00",  # yellow
            "#ffc000",
            "#ff8000",
            "#ff4000",
            "#ff0000",  # red
        ]

    def update_visualizer(self, data: VisualizerData) -> None:
        self.bars = data.bars
        self.peak = data.peak
        self.refresh()

    def render(self) -> str:
        if len(self.bars) == 0:
            return ""

        lines = []
        height = 8

        for h in range(height, 0, -1):
            line = ""
            for i, val in enumerate(self.bars):
                bar_height = val * height
                if bar_height >= h:
                    char_idx = min(int((bar_height - h) * 8), 7)
                    color = self._colors[min(i // 4, 7)]
                    line += f"[{color}]{self._bar_chars[char_idx]}[/{color}]"
                else:
                    line += " "
            lines.append(line)

        return "\n".join(lines)


# ── Login Screen ──

class LoginScreen(Screen):
    """Screen for Google OAuth2 login."""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(classes="login-container"):
            yield Label("Terminal Music Downloader", classes="title")
            yield Label("Connect your Google account to sync liked songs", classes="subtitle")
            yield Static("", id="login-status")
            yield Button("Sign in with Google", variant="primary", id="login-btn")
        yield Footer()

    def on_mount(self) -> None:
        self._check_credentials()

    def _check_credentials(self) -> None:
        """Show warning if OAuth credentials are not configured."""
        status = self.query_one("#login-status", Static)
        app = self.app
        if isinstance(app, TMDApp):
            if not app.settings.youtube_client_id or not app.settings.youtube_client_secret:
                status.update(
                    "[yellow]⚠ Warning: Google OAuth credentials not configured.\n"
                    "Set TMD_YOUTUBE_CLIENT_ID and TMD_YOUTUBE_CLIENT_SECRET environment variables,\n"
                    "or edit ~/.config/tmd/settings.json[/yellow]"
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login-btn":
            self.app.action_login()


# ── Library Screen ──

class LibraryScreen(Screen):
    """Main library screen showing liked songs."""

    songs = reactive([])
    current_song: Optional[Song] = None

    BINDINGS = [
        Binding("enter", "play_selected", "Play"),
        Binding("space", "toggle_play", "Play/Pause"),
        Binding("n", "next_song", "Next"),
        Binding("p", "prev_song", "Previous"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield Label("Your Liked Songs", classes="screen-title")
            yield DataTable(id="library-table")
            with Horizontal(classes="player-panel"):
                yield Static("Now Playing: ", id="now-playing")
                yield ProgressBar(id="song-progress", total=100)
                yield VisualizerWidget(id="visualizer")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#library-table", DataTable)
        table.add_columns("#", "Title", "Artist", "Duration", "Status")
        self.update_library()

    def update_library(self) -> None:
        table = self.query_one("#library-table", DataTable)
        table.clear()
        for i, song in enumerate(self.songs, 1):
            duration = f"{song.duration_secs // 60}:{song.duration_secs % 60:02d}" if song.duration_secs else "??:??"
            status_icon = {
                "pending": "⏳",
                "downloading": "📥",
                "completed": "✅",
                "failed": "❌",
                "permanently_failed": "💀",
            }.get(song.download_status, "❓")
            table.add_row(str(i), song.title, song.artist, duration, status_icon, key=song.video_id)

    def watch_songs(self, songs: List[Song]) -> None:
        self.update_library()

    def action_play_selected(self) -> None:
        table = self.query_one("#library-table", DataTable)
        if table.cursor_row is not None:
            row_key = table.get_row_at(table.cursor_row)
            # Find song by video_id
            video_id = row_key[0] if row_key else None
            if video_id:
                for song in self.songs:
                    if song.video_id == video_id:
                        self.app.action_play_song(song)
                        break

    def action_toggle_play(self) -> None:
        self.app.action_toggle_play()

    def action_next_song(self) -> None:
        self.app.action_next_song()

    def action_prev_song(self) -> None:
        self.app.action_prev_song()


# ── Search Screen ──

class SearchScreen(Screen):
    """Screen for searching and downloading new songs."""

    results = reactive([])

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield Input(placeholder="Search YouTube...", id="search-input")
            yield DataTable(id="search-results")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#search-results", DataTable)
        table.add_columns("Title", "Artist", "Published")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            self.app.action_search(event.value)

    def watch_results(self, results: List[dict]) -> None:
        table = self.query_one("#search-results", DataTable)
        table.clear()
        for result in results:
            table.add_row(
                result["title"],
                result["artist"],
                result["published_at"][:10],
                key=result["video_id"],
            )

    def action_download_selected(self) -> None:
        table = self.query_one("#search-results", DataTable)
        if table.cursor_row is not None:
            row = table.get_row_at(table.cursor_row)
            if row:
                video_id = row[0]
                self.app.action_download_and_like(video_id)


# ── Settings Screen ──

class SettingsScreen(Screen):
    """Screen for application settings."""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(classes="settings-container"):
            yield Label("Settings", classes="screen-title")
            yield Label("Audio Quality:")
            yield Button("128k", id="quality-128")
            yield Button("192k", id="quality-192")
            yield Button("256k", id="quality-256")
            yield Button("320k", id="quality-320")
            yield Label("")
            yield Button("Logout", variant="error", id="logout-btn")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id and btn_id.startswith("quality-"):
            quality = btn_id.split("-")[1] + "k"
            self.app.settings.audio_quality = quality
            self.app.settings.save(get_settings_path())
            self.notify(f"Quality set to {quality}")
        elif btn_id == "logout-btn":
            self.app.action_logout()


# ── Main App ──

import numpy as np


class TMDApp(App):
    """Terminal Music Downloader application."""

    CSS = """
    Screen {
        align: center middle;
    }
    
    .login-container {
        width: 60;
        height: auto;
        border: thick $background 80%;
        padding: 2 4;
        background: $surface-darken-1;
    }
    
    .title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    .subtitle {
        text-align: center;
        color: $text-muted;
        margin-bottom: 2;
    }
    
    .screen-title {
        text-style: bold;
        color: $accent;
        margin: 1 0;
    }
    
    .player-panel {
        height: 12;
        background: $surface-darken-1;
        padding: 1 2;
    }
    
    #visualizer {
        width: 1fr;
        height: 8;
    }
    
    #library-table, #search-results {
        height: 1fr;
    }
    
    .settings-container {
        width: 40;
        height: auto;
        padding: 2;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("/", "push_search", "Search"),
        Binding("comma", "push_settings", "Settings"),
    ]

    SCREENS = {
        "login": LoginScreen,
        "library": LibraryScreen,
        "search": SearchScreen,
        "settings": SettingsScreen,
    }

    def __init__(self):
        super().__init__()
        self.settings = Settings.load(get_settings_path())
        self.db = Database(get_database_path())
        self.player = AudioPlayer(
            visualizer_callback=self._on_visualizer_update,
            num_bars=self.settings.visualizer_bars,
        )
        self.download_manager: Optional[DownloadManager] = None
        self.creds: Optional[Credentials] = None
        self.current_song_index: int = 0

    def on_mount(self) -> None:
        if is_authenticated():
            self.push_screen("library")
            asyncio.create_task(self._startup_sync())
        else:
            self.push_screen("login")

    async def _startup_sync(self) -> None:
        try:
            from tmd.auth import load_credentials
            self.creds = load_credentials()
            if self.creds:
                new_songs = sync_liked_songs(self.creds, self.db)
                if new_songs:
                    self.notify(f"Found {len(new_songs)} new liked songs!")
                    if not self.download_manager:
                        self.download_manager = DownloadManager(
                            self.db,
                            self.settings.download_dir,
                            self.settings.audio_quality,
                            self.settings.max_concurrent_downloads,
                            progress_callback=self._on_download_progress,
                        )
                        self.download_manager.start()
                    self.download_manager.queue_songs(new_songs)
                self._refresh_library()
        except SyncError as e:
            self.notify(_clean_msg(str(e)), severity="error", timeout=15)
        except Exception as e:
            import traceback
            err_msg = f"Sync failed: {e}"
            self.notify(_clean_msg(err_msg), severity="error")
            print(f"\n[DEBUG] {err_msg}")
            traceback.print_exc()

    def _refresh_library(self) -> None:
        library_screen = self.get_screen("library")
        if isinstance(library_screen, LibraryScreen):
            library_screen.songs = self.db.get_all_songs()

    def _on_visualizer_update(self, data: VisualizerData) -> None:
        try:
            visualizer = self.query_one("#visualizer", VisualizerWidget)
            visualizer.update_visualizer(data)
        except NoMatches:
            pass

    def _on_download_progress(self, progress: DownloadProgress) -> None:
        self._refresh_library()

    def action_login(self) -> None:
        async def do_login():
            try:
                from tmd.auth import authenticate
                self.creds = authenticate(
                    self.settings.youtube_client_id,
                    self.settings.youtube_client_secret,
                )
                self.switch_screen("library")
                await self._startup_sync()
            except AuthenticationError as e:
                # Show multi-line error as a notification
                self.notify(_clean_msg(str(e)), severity="error", timeout=15)
            except Exception as e:
                self.notify(_clean_msg(f"Login failed: {e}"), severity="error")

        asyncio.create_task(do_login())

    def action_logout(self) -> None:
        logout()
        self.player.stop()
        if self.download_manager:
            self.download_manager.stop()
        self.switch_screen("login")

    def action_push_search(self) -> None:
        self.push_screen("search")

    def action_push_settings(self) -> None:
        self.push_screen("settings")

    def action_search(self, query: str) -> None:
        async def do_search():
            try:
                if not self.creds:
                    self.creds = load_credentials()
                results = search_youtube(self.creds, query)
                search_screen = self.get_screen("search")
                if isinstance(search_screen, SearchScreen):
                    search_screen.results = results
            except Exception as e:
                self.notify(_clean_msg(f"Search failed: {e}"), severity="error")

        asyncio.create_task(do_search())

    def action_download_and_like(self, video_id: str) -> None:
        async def do_download():
            try:
                if not self.creds:
                    self.creds = load_credentials()

                # Check if already liked
                if self.db.song_exists(video_id):
                    self.notify("Song already in library!", severity="warning")
                    return

                # Add to liked playlist
                success = add_to_liked_playlist(self.creds, video_id)
                if success:
                    self.notify("Added to liked songs!")
                else:
                    self.notify("Failed to add to liked playlist", severity="warning")

                # Get song info and add to library
                results = search_youtube(self.creds, video_id, max_results=1)
                if results:
                    song_data = results[0]
                    song = Song(
                        video_id=video_id,
                        title=song_data["title"],
                        artist=song_data["artist"],
                        duration_secs=0,
                        thumbnail_url=song_data["thumbnail"],
                        file_path="",
                        added_to_yt_at=None,
                        downloaded_at=None,
                        download_status="pending",
                        retry_count=0,
                    )
                    self.db.insert_song(song)
                    if self.download_manager:
                        self.download_manager.queue_song(song)
                    self._refresh_library()
            except Exception as e:
                self.notify(_clean_msg(f"Download failed: {e}"), severity="error")

        asyncio.create_task(do_download())

    def action_play_song(self, song: Song) -> None:
        if song.file_path and Path(song.file_path).exists():
            self.player.stop()
            if self.player.load(Path(song.file_path)):
                self.player.play()
                self.current_song_index = self.db.get_all_songs().index(song)
                try:
                    now_playing = self.query_one("#now-playing", Static)
                    now_playing.update(f"Now Playing: {song.title} - {song.artist}")
                except NoMatches:
                    pass
                self.notify(f"Playing: {song.title}")
            else:
                self.notify("Failed to load song", severity="error")
        else:
            self.notify("Song not downloaded yet", severity="warning")

    def action_toggle_play(self) -> None:
        self.player.toggle_playback()
        state = "Playing" if self.player.state == PlaybackState.PLAYING else "Paused"
        self.notify(state)

    def action_next_song(self) -> None:
        songs = self.db.get_all_songs()
        if songs:
            self.current_song_index = (self.current_song_index + 1) % len(songs)
            self.action_play_song(songs[self.current_song_index])

    def action_prev_song(self) -> None:
        songs = self.db.get_all_songs()
        if songs:
            self.current_song_index = (self.current_song_index - 1) % len(songs)
            self.action_play_song(songs[self.current_song_index])

    def action_quit(self) -> None:
        self.player.stop()
        if self.download_manager:
            self.download_manager.stop()
        self.exit()


