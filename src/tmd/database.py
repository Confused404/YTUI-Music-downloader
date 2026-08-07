"""SQLite database layer for song library."""

import sqlite3
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class Song:
    video_id: str
    title: str
    artist: str
    duration_secs: int
    thumbnail_url: str
    file_path: str
    added_to_yt_at: Optional[str]
    downloaded_at: Optional[str]
    download_status: str  # pending | downloading | completed | failed | permanently_failed
    retry_count: int = 0


class Database:
    """Manages the SQLite library database."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS songs (
                    video_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    duration_secs INTEGER DEFAULT 0,
                    thumbnail_url TEXT DEFAULT '',
                    file_path TEXT DEFAULT '',
                    added_to_yt_at TEXT,
                    downloaded_at TEXT,
                    download_status TEXT DEFAULT 'pending',
                    retry_count INTEGER DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_added_to_yt_at 
                ON songs(added_to_yt_at DESC)
                """
            )
            conn.commit()

    def insert_song(self, song: Song) -> None:
        """Insert a new song or replace existing."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO songs 
                (video_id, title, artist, duration_secs, thumbnail_url, file_path, 
                 added_to_yt_at, downloaded_at, download_status, retry_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    song.video_id,
                    song.title,
                    song.artist,
                    song.duration_secs,
                    song.thumbnail_url,
                    song.file_path,
                    song.added_to_yt_at,
                    song.downloaded_at,
                    song.download_status,
                    song.retry_count,
                ),
            )
            conn.commit()

    def get_song(self, video_id: str) -> Optional[Song]:
        """Get a single song by video ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM songs WHERE video_id = ?", (video_id,)
            ).fetchone()
            if row:
                return Song(**dict(row))
            return None

    def get_all_songs(self) -> List[Song]:
        """Get all songs sorted by added_to_yt_at DESC."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM songs ORDER BY added_to_yt_at DESC"
            ).fetchall()
            return [Song(**dict(row)) for row in rows]

    def get_pending_songs(self) -> List[Song]:
        """Get all songs with pending or failed status."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM songs 
                WHERE download_status IN ('pending', 'failed')
                AND retry_count < 3
                ORDER BY added_to_yt_at DESC
                """
            ).fetchall()
            return [Song(**dict(row)) for row in rows]

    def update_download_status(
        self, video_id: str, status: str, file_path: str = ""
    ) -> None:
        """Update the download status of a song."""
        downloaded_at = datetime.now().isoformat() if status == "completed" else None
        with self._connect() as conn:
            if file_path:
                conn.execute(
                    """
                    UPDATE songs 
                    SET download_status = ?, file_path = ?, downloaded_at = ?
                    WHERE video_id = ?
                    """,
                    (status, file_path, downloaded_at, video_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE songs 
                    SET download_status = ?, downloaded_at = ?
                    WHERE video_id = ?
                    """,
                    (status, downloaded_at, video_id),
                )
            conn.commit()

    def increment_retry(self, video_id: str) -> None:
        """Increment the retry counter for a song."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE songs 
                SET retry_count = retry_count + 1,
                    download_status = CASE 
                        WHEN retry_count + 1 >= 3 THEN 'permanently_failed' 
                        ELSE 'failed' 
                    END
                WHERE video_id = ?
                """,
                (video_id,),
            )
            conn.commit()

    def get_known_video_ids(self) -> set:
        """Get all known video IDs as a set."""
        with self._connect() as conn:
            rows = conn.execute("SELECT video_id FROM songs").fetchall()
            return {row["video_id"] for row in rows}

    def song_exists(self, video_id: str) -> bool:
        """Check if a song already exists in the library."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM songs WHERE video_id = ? LIMIT 1", (video_id,)
            ).fetchone()
            return row is not None
