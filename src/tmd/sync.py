"""YouTube liked songs sync engine."""

from typing import List, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

from tmd.database import Database, Song


# YouTube "Liked Videos" playlist ID (same for all users)
LIKED_PLAYLIST_ID = "LL"


class SyncError(Exception):
    """Raised when sync fails with a helpful message."""
    pass


def fetch_liked_songs(creds: Credentials) -> List[Dict[str, Any]]:
    """Fetch all videos from the liked playlist."""
    youtube = build("youtube", "v3", credentials=creds)

    songs = []
    next_page_token = None

    try:
        while True:
            request = youtube.playlistItems().list(
                part="snippet",
                playlistId=LIKED_PLAYLIST_ID,
                maxResults=50,
                pageToken=next_page_token,
            )
            response = request.execute()

            for item in response["items"]:
                snippet = item["snippet"]
                song = {
                    "video_id": snippet["resourceId"]["videoId"],
                    "title": snippet["title"],
                    "artist": snippet.get("videoOwnerChannelTitle", "Unknown Artist"),
                    "added_to_yt_at": snippet["publishedAt"],
                }
                songs.append(song)

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

    except HttpError as e:
        status = e.resp.status
        if status == 403:
            raise SyncError(
                "YouTube API access denied (403).\n\n"
                "Common fixes:\n"
                "1. Make sure YouTube Data API v3 is ENABLED in your Google Cloud project:\n"
                "   https://console.cloud.google.com/apis/library/youtube.googleapis.com\n"
                "2. Make sure your email is added as a TEST USER:\n"
                "   https://console.cloud.google.com/apis/credentials/consent\n"
                "3. Make sure you have at least 1 liked song on YouTube Music"
            ) from e
        elif status == 404:
            raise SyncError(
                "Liked songs playlist not found.\n"
                "Make sure you have at least 1 liked song on YouTube Music."
            ) from e
        else:
            raise SyncError(f"YouTube API error {status}: {e}") from e

    return songs


def sync_liked_songs(creds: Credentials, db: Database) -> List[Song]:
    """Sync liked songs and return newly added songs."""
    remote_songs = fetch_liked_songs(creds)
    known_ids = db.get_known_video_ids()

    new_songs = []
    for song_data in remote_songs:
        video_id = song_data["video_id"]
        if video_id not in known_ids:
            song = Song(
                video_id=video_id,
                title=song_data["title"],
                artist=song_data["artist"],
                duration_secs=0,
                thumbnail_url=f"https://img.youtube.com/vi/{video_id}/default.jpg",
                file_path="",
                added_to_yt_at=song_data["added_to_yt_at"],
                downloaded_at=None,
                download_status="pending",
                retry_count=0,
            )
            db.insert_song(song)
            new_songs.append(song)

    return new_songs
