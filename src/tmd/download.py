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

        # Check if already downloaded
        if output_path.exists() and song.download_status == "completed":
            return True

        self.db.update_download_status(song.video_id, "downloading")
        if self.progress_callback:
            self.progress_callback(
                DownloadProgress(song.video_id, 0.0, "downloading")
            )

        cmd = [
            "yt-dlp",
            "-x",
            "--audio-format",
            "mp3",
            "--audio-quality",
            self.audio_quality,
            "--output",
            str(output_path.with_suffix(".%(ext)s")),
            "--newline",
            f"https://www.youtube.com/watch?v={song.video_id}",
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Parse progress from stdout
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                line = line.decode("utf-8", errors="replace")

                # Parse download progress
                match = re.search(r"\[download\]\s+(\d+\.?\d*)%", line)
                if match and self.progress_callback:
                    percent = float(match.group(1))
                    self.progress_callback(
                        DownloadProgress(song.video_id, percent, "downloading")
                    )

            await process.wait()

            if process.returncode == 0:
                self.db.update_download_status(
                    song.video_id, "completed", str(output_path)
                )
                if self.progress_callback:
                    self.progress_callback(
                        DownloadProgress(song.video_id, 100.0, "completed")
                    )
                return True
            else:
                raise subprocess.CalledProcessError(process.returncode, cmd)

        except Exception:
            self.db.increment_retry(song.video_id)
            if self.progress_callback:
                self.progress_callback(
                    DownloadProgress(song.video_id, 0.0, "failed")
                )
            return False

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
        self._running = True
        for _ in range(self.max_concurrent):
            task = asyncio.create_task(self._worker())
            self._workers.append(task)

    def stop(self) -> None:
        """Stop the download manager."""
        self._running = False
        for worker in self._workers:
            worker.cancel()
        self._workers.clear()

    def queue_song(self, song: Song) -> None:
        """Add a song to the download queue."""
        self._queue.put_nowait(song)

    def queue_songs(self, songs: List[Song]) -> None:
        """Add multiple songs to the download queue."""
        for song in songs:
            self.queue_song(song)
