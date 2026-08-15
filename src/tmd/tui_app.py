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
from tmd.auth import is_authenticated, logout, Credentials, AuthenticationError, TokenExpiredError
from googleapiclient.discovery import build
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


# ── Auth Banner ──

class AuthBanner(Static):
    """Dismissible banner shown when OAuth token expires."""

    def compose(self) -> ComposeResult:
        with Horizontal(classes="auth-banner"):
            yield Label("⚠ Session expired", classes="auth-banner-text")
            yield Button("Re-authenticate", variant="primary", id="reauth-btn")
            yield Button("✕", variant="error", id="dismiss-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "reauth-btn":
            app = self.app
            if isinstance(app, TMDApp):
                app.action_login()
        elif event.button.id == "dismiss-btn":
            self.display = False


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
    current_song_id: Optional[str] = None
    download_progress: reactive[dict] = reactive({})

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

    def _format_status(self, song: Song) -> str:
        """Format the status column with progress and current-song indicators."""
        # Check if currently playing
        if song.video_id == self.current_song_id:
            if self.app.player.state.name == "PLAYING":
                return "▶ Playing"
            else:
                return "⏸ Paused"

        # Show download progress
        if song.download_status == "downloading":
            pct = self.download_progress.get(song.video_id, 0)
            bar_width = 8
            filled = int(pct / 100 * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)
            return f"📥 {bar} {pct:.0f}%"

        status_icons = {
            "pending": "⏳ Pending",
            "completed": "✅ Ready",
            "failed": "❌ Failed",
            "permanently_failed": "💀 Failed",
        }
        return status_icons.get(song.download_status, "❓ Unknown")

    def update_library(self) -> None:
        table = self.query_one("#library-table", DataTable)
        table.clear()
        num_cols = len(table.columns)
        if num_cols == 0:
            # Columns not ready yet, skip
            return
        for i, song in enumerate(self.songs, 1):
            duration = f"{song.duration_secs // 60}:{song.duration_secs % 60:02d}" if song.duration_secs else "??:??"
            status = self._format_status(song)
            cells = [str(i), song.title, song.artist, duration, status]
            if len(cells) != num_cols:
                print(f"[DEBUG] Column mismatch: {len(cells)} cells vs {num_cols} columns")
                continue
            try:
                table.add_row(*cells)
            except Exception as e:
                print(f"[DEBUG] add_row failed for '{song.title}': {e}")
                print(f"[DEBUG] Cells: {cells}")
                # Don't crash, just skip this row

    def watch_songs(self, songs: List[Song]) -> None:
        self.update_library()

    def watch_current_song_id(self, song_id: Optional[str]) -> None:
        self.update_library()

    def watch_download_progress(self, progress: dict) -> None:
        self.update_library()

    def action_play_selected(self) -> None:
        table = self.query_one("#library-table", DataTable)
        if table.cursor_row is not None:
            idx = table.cursor_row
            if 0 <= idx < len(self.songs):
                self.app.action_play_song(self.songs[idx])

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

    BINDINGS = [
        Binding("escape", "pop_screen", "Back", show=False),
        Binding("d", "download_selected", "Download"),
    ]

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
        if table.cursor_row is not None and self.results:
            row_idx = table.cursor_row
            if 0 <= row_idx < len(self.results):
                video_id = self.results[row_idx]["video_id"]
                self.app.action_download_and_like(video_id)


# ── Settings Screen ──

class SettingsScreen(Screen):
    """Screen for application settings."""

    BINDINGS = [
        Binding("escape", "pop_screen", "Back", show=False),
    ]

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
    
    .auth-banner {
        dock: bottom;
        height: 3;
        align: right middle;
        background: $surface-darken-2;
        color: $warning;
        padding: 0 2;
    }
    
    .auth-banner-text {
        content-align: center middle;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("/", "push_search", "Search"),
        Binding("comma", "push_settings", "Settings"),
    ]

    SCREENS = {
        "login": LoginScreen,
        "library": LibraryScreen,
        "search": SearchScreen,
        "settings": SettingsScreen,
    }

    auth_expired = reactive(False)

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
        self.download_progress: dict = {}  # video_id -> percent
        self.auth_banner: Optional[AuthBanner] = None

    def on_mount(self) -> None:
        # Mount auth banner at app level (persists across screens)
        self.auth_banner = AuthBanner()
        self.mount(self.auth_banner)
        self.auth_banner.display = False

        if is_authenticated():
            self.push_screen("library")
            asyncio.create_task(self._startup_sync())
        else:
            self.push_screen("login")

    def watch_auth_expired(self, expired: bool) -> None:
        """Show/hide auth banner based on reactive flag."""
        if self.auth_banner:
            self.auth_banner.display = expired

    async def _startup_sync(self) -> None:
        try:
            from tmd.auth import load_credentials
            self.creds = load_credentials()
            if self.creds:
                # Clear auth expired flag on successful credential load
                self.auth_expired = False
                # TODO: wire self.settings.filter_music_only when a settings toggle is added
                new_songs = sync_liked_songs(self.creds, self.db, filter_music_only=True)
                pending_songs = self.db.get_pending_songs()

                if new_songs:
                    self.notify(f"Found {len(new_songs)} new liked songs!")

                if new_songs or pending_songs:
                    self._ensure_download_manager()
                    if new_songs:
                        self.download_manager.queue_songs(new_songs)
                    if pending_songs:
                        self.download_manager.queue_songs(pending_songs)
                        self.notify(f"Queued {len(pending_songs)} pending downloads")

                self._refresh_library()
                # Pass download progress to library screen
                library_screen = self.get_screen("library")
                if isinstance(library_screen, LibraryScreen):
                    library_screen.download_progress = self.download_progress
        except TokenExpiredError:
            # Silently show auth banner — no error toast
            self.auth_expired = True
            self.creds = None
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
            library_screen.download_progress = self.download_progress

    def _on_visualizer_update(self, data: VisualizerData) -> None:
        try:
            visualizer = self.query_one("#visualizer", VisualizerWidget)
            visualizer.update_visualizer(data)
        except NoMatches:
            pass

    def _on_download_progress(self, progress: DownloadProgress) -> None:
        self.download_progress[progress.video_id] = progress.percent
        self._refresh_library()
        # Clean up completed downloads from progress tracker
        if progress.status == "completed":
            self.download_progress.pop(progress.video_id, None)

    def action_login(self) -> None:
        async def do_login():
            try:
                from tmd.auth import authenticate
                self.creds = authenticate(
                    self.settings.youtube_client_id,
                    self.settings.youtube_client_secret,
                )
                # Clear auth expired flag on successful login
                self.auth_expired = False
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
            except TokenExpiredError:
                self.auth_expired = True
                self.creds = None
            except Exception as e:
                self.notify(_clean_msg(f"Search failed: {e}"), severity="error")

        asyncio.create_task(do_search())

    def _ensure_download_manager(self) -> None:
        """Initialize download manager if not already running."""
        if not self.download_manager:
            self.download_manager = DownloadManager(
                self.db,
                self.settings.download_dir,
                self.settings.audio_quality,
                self.settings.max_concurrent_downloads,
                progress_callback=self._on_download_progress,
            )
            self.download_manager.start()

    def action_download_and_like(self, video_id: str) -> None:
        async def do_download():
            try:
                if not self.creds:
                    self.creds = load_credentials()

                # Check if already liked
                if self.db.song_exists(video_id):
                    self.notify("Song already in library!", severity="warning")
                    return

                # Get video info first
                youtube = build("youtube", "v3", credentials=self.creds)
                video_response = youtube.videos().list(
                    part="snippet,contentDetails",
                    id=video_id,
                ).execute()

                if not video_response["items"]:
                    self.notify("Video not found!", severity="error")
                    return

                video = video_response["items"][0]
                snippet = video["snippet"]
                song = Song(
                    video_id=video_id,
                    title=snippet["title"],
                    artist=snippet.get("channelTitle", "Unknown"),
                    duration_secs=0,
                    thumbnail_url=snippet["thumbnails"]["default"]["url"],
                    file_path="",
                    added_to_yt_at=None,
                    downloaded_at=None,
                    download_status="pending",
                    retry_count=0,
                )
                self.db.insert_song(song)

                # Add to liked playlist
                success = add_to_liked_playlist(self.creds, video_id)
                if success:
                    self.notify("Added to liked songs!")
                else:
                    self.notify("Failed to add to liked playlist (downloading anyway)", severity="warning")

                # Ensure download manager is running and queue
                self._ensure_download_manager()
                self.download_manager.queue_song(song)
                self._refresh_library()
            except TokenExpiredError:
                self.auth_expired = True
                self.creds = None
            except Exception as e:
                print(f"[DOWNLOAD ERROR] action_download_and_like: {e}")
                import traceback
                traceback.print_exc()
                self.notify(_clean_msg(f"Download failed: {e}"), severity="error")

        asyncio.create_task(do_download())

    def action_play_song(self, song: Song) -> None:
        if song.file_path and Path(song.file_path).exists():
            self.player.stop()
            if self.player.load(Path(song.file_path)):
                self.player.play()
                self.current_song_index = self.db.get_all_songs().index(song)
                # Update library highlight
                library_screen = self.get_screen("library")
                if isinstance(library_screen, LibraryScreen):
                    library_screen.current_song_id = song.video_id
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


