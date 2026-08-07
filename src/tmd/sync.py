"""YouTube liked songs sync engine."""

from typing import List, Dict, Any
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from tmd.database import Database, Song


# YouTube "Liked Videos" playlist ID (same for all users)
LIKED_PLAYLIST_ID = "LL"


def fetch_liked_songs(creds: Credentials) -> List[Dict[str, Any]]:
    """Fetch all videos from the liked playlist."""
    youtube = build("youtube", "v3", credentials=creds)

    songs = []
    next_page_token = None

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
