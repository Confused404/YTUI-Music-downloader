"""Download manager using yt-dlp."""

import re
import asyncio
import subprocess
from pathlib import Path
from typing import Callable, Optional, List
from dataclasses import dataclass

from tmd.database import Database, Song
from tmd.config import get_music_dir


@dataclass
class DownloadProgress:
    video_id: str
    percent: float
    status: str  # pending | downloading | completed | failed


class DownloadManager:
    """Manages concurrent song downloads using yt-dlp."""

    def __init__(
        self,
        db: Database,
        download_dir: Path,
        audio_quality: str = "192k",
        max_concurrent: int = 2,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
    ):
        self.db = db
        self.download_dir = download_dir
        self.audio_quality = audio_quality
        self.max_concurrent = max_concurrent
        self.progress_callback = progress_callback
        self._queue: asyncio.Queue[Song] = asyncio.Queue()
        self._workers: List[asyncio.Task] = []
        self._running = False

    def _sanitize_filename(self, name: str) -> str:
        """Remove characters illegal in filenames."""
        return re.sub(r'[\\/:*?"<>|]', "", name).strip()

    def _build_output_path(self, song: Song) -> Path:
        """Build the output file path for a song."""
        filename = f"{self._sanitize_filename(song.artist)} - {self._sanitize_filename(song.title)}"
        return self.download_dir / f"{filename}.mp3"

    async def _download_song(self, song: Song) -> bool:
        """Download a single song. Returns True on success."""
        output_path = self._build_output_path(song)
        print(f"[DOWNLOAD] Starting: {song.title} ({song.video_id})")

        # Check if already downloaded
        if output_path.exists() and song.download_status == "completed":
            print(f"[DOWNLOAD] Already exists: {output_path}")
            return True

        self.db.update_download_status(song.video_id, "downloading")
        if self.progress_callback:
            self.progress_callback(
                DownloadProgress(song.video_id, 0.0, "downloading")
            )

        # Use a simple output template with video_id to make it trackable
        output_template = str(self.download_dir / f"{song.video_id}.%(ext)s")

        cmd = [
            "yt-dlp",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", self.audio_quality,
            "--output", output_template,
            "--newline",
            "--no-warnings",
            "--no-playlist",
            f"https://www.youtube.com/watch?v={song.video_id}",
        ]

        print(f"[DOWNLOAD] Command: {' '.join(cmd[:8])} ...")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stderr_lines = []
            last_percent = 0

            # Read stdout and stderr concurrently
            async def read_stdout():
                nonlocal last_percent
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace").strip()
                    if text:
                        print(f"[yt-dlp stdout] {text[:120]}")
                    # Parse download progress
                    match = re.search(r"\[download\]\s+(\d+\.?\d*)%", text)
                    if match and self.progress_callback:
                        percent = float(match.group(1))
                        if percent != last_percent:
                            last_percent = percent
                            self.progress_callback(
                                DownloadProgress(song.video_id, percent, "downloading")
                            )

            async def read_stderr():
                while True:
                    line = await process.stderr.readline()
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace").strip()
                    if text:
                        stderr_lines.append(text)
                        print(f"[yt-dlp stderr] {text[:120]}")

            await asyncio.gather(read_stdout(), read_stderr())
            await process.wait()

            print(f"[DOWNLOAD] Exit code for '{song.title}': {process.returncode}")

            if process.returncode == 0:
                # Find the actual downloaded file
                actual_file = self._find_downloaded_file(song)
                file_path = str(actual_file) if actual_file else str(output_path)
                self.db.update_download_status(song.video_id, "completed", file_path)
                if self.progress_callback:
                    self.progress_callback(
                        DownloadProgress(song.video_id, 100.0, "completed")
                    )
                print(f"[DOWNLOAD] Completed: {song.title} -> {file_path}")
                return True
            else:
                error_msg = "\n".join(stderr_lines[-5:]) if stderr_lines else f"Exit code {process.returncode}"
                print(f"[DOWNLOAD ERROR] {song.title}: {error_msg}")
                raise subprocess.CalledProcessError(process.returncode, cmd)

        except Exception as e:
            print(f"[DOWNLOAD ERROR] {song.title}: {e}")
            self.db.increment_retry(song.video_id)
            if self.progress_callback:
                self.progress_callback(
                    DownloadProgress(song.video_id, 0.0, "failed")
                )
            return False

    def _find_downloaded_file(self, song: Song) -> Optional[Path]:
        """Find the actual downloaded MP3 file for a song."""
        expected = self._build_output_path(song)
        if expected.exists():
            return expected

        # Try to find by video_id in filename
        for f in self.download_dir.iterdir():
            if f.suffix == ".mp3" and song.video_id in f.name:
                return f
        return None

    async def _worker(self) -> None:
        """Worker that processes downloads from the queue."""
        while self._running:
            try:
                song = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._download_song(song)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue

    def start(self) -> None:
        """Start the download manager workers."""
        print(f"[DOWNLOAD] Starting manager with {self.max_concurrent} workers")
        self._running = True
        for _ in range(self.max_concurrent):
            task = asyncio.create_task(self._worker())
            self._workers.append(task)

    def stop(self) -> None:
        """Stop the download manager."""
        print("[DOWNLOAD] Stopping manager")
        self._running = False
        for worker in self._workers:
            worker.cancel()
        self._workers.clear()

    def queue_song(self, song: Song) -> None:
        """Add a song to the download queue."""
        print(f"[DOWNLOAD] Queued: {song.title}")
        self._queue.put_nowait(song)

    def queue_songs(self, songs: List[Song]) -> None:
        """Add multiple songs to the download queue."""
        print(f"[DOWNLOAD] Queuing {len(songs)} songs")
        for song in songs:
            self.queue_song(song)
