"""YouTube liked songs sync engine."""

import re
from typing import List, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

from tmd.database import Database, Song


# YouTube "Liked Videos" playlist ID (same for all users)
LIKED_PLAYLIST_ID = "LL"

# ISO 8601 duration regex: PT1H2M3S, PT45S, PT3M, etc.
_DURATION_RE = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")

# Music channel markers for Pass 1 heuristic (zero API cost)
_MUSIC_CHANNEL_KEYWORDS = ("vevo", " - topic", "official", "music")


class SyncError(Exception):
    """Raised when sync fails with a helpful message."""
    pass


def _parse_duration(iso_duration: str) -> int:
    """Parse a YouTube ISO 8601 duration string into integer seconds."""
    match = _DURATION_RE.fullmatch(iso_duration)
    if not match:
        return 0
    hours, minutes, seconds = match.groups()
    total = 0
    if hours:
        total += int(hours) * 3600
    if minutes:
        total += int(minutes) * 60
    if seconds:
        total += int(seconds)
    return total


def _is_music_channel(channel_title: str) -> bool:
    """Return True if the channel title strongly suggests a music upload."""
    if not channel_title:
        return False
    lower = channel_title.lower()
    return any(marker in lower for marker in _MUSIC_CHANNEL_KEYWORDS)


def _fetch_video_details(
    youtube, video_ids: List[str]
) -> Dict[str, Dict[str, Any]]:
    """Batch-fetch snippet+contentDetails for up to 50 IDs per API call.
    Returns {video_id: {"duration_secs": int, "category_id": str}}
    """
    details: Dict[str, Dict[str, Any]] = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        response = (
            youtube.videos()
            .list(part="snippet,contentDetails", id=",".join(batch))
            .execute()
        )
        for item in response.get("items", []):
            vid = item["id"]
            details[vid] = {
                "duration_secs": _parse_duration(item["contentDetails"]["duration"]),
                "category_id": item["snippet"].get("categoryId", ""),
            }
    return details


def fetch_liked_songs(
    creds: Credentials, filter_music_only: bool = True
) -> List[Dict[str, Any]]:
    """Fetch all videos from the liked playlist with real durations."""
    youtube = build("youtube", "v3", credentials=creds)

    songs = []
    video_ids: List[str] = []
    next_page_token = None

    try:
        # Step 1: collect all playlist items
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
                video_id = snippet["resourceId"]["videoId"]
                video_ids.append(video_id)
                song = {
                    "video_id": video_id,
                    "title": snippet["title"],
                    "artist": snippet.get("videoOwnerChannelTitle", "Unknown Artist"),
                    "added_to_yt_at": snippet["publishedAt"],
                }
                songs.append(song)

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        # Step 2: single batch call for snippet (categoryId) + contentDetails (duration)
        details = _fetch_video_details(youtube, video_ids)

        # Step 3: merge durations and optionally apply tiered music filter
        result = []
        for song in songs:
            vid = song["video_id"]
            detail = details.get(vid, {})
            duration = detail.get("duration_secs", 0)
            category_id = detail.get("category_id", "")
            song["duration_secs"] = duration

            if not filter_music_only:
                result.append(song)
                continue

            # Pass 1: channel-name heuristic (free)
            if _is_music_channel(song["artist"]):
                result.append(song)
            # Pass 2: categoryId == 10 (Music)
            elif category_id == "10":
                result.append(song)
            # Pass 2: duration gate + title pattern
            elif 60 <= duration <= 600 and " - " in song["title"]:
                result.append(song)
            # Otherwise: silently drop as non-music

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

    return result


def sync_liked_songs(
    creds: Credentials, db: Database, filter_music_only: bool = True
) -> List[Song]:
    """Sync liked songs and return newly added songs."""
    remote_songs = fetch_liked_songs(creds, filter_music_only=filter_music_only)
    known_ids = db.get_known_video_ids()

    new_songs = []
    for song_data in remote_songs:
        video_id = song_data["video_id"]
        duration_secs = song_data.get("duration_secs", 0)

        if video_id not in known_ids:
            song = Song(
                video_id=video_id,
                title=song_data["title"],
                artist=song_data["artist"],
                duration_secs=duration_secs,
                thumbnail_url=f"https://img.youtube.com/vi/{video_id}/default.jpg",
                file_path="",
                added_to_yt_at=song_data["added_to_yt_at"],
                downloaded_at=None,
                download_status="pending",
                retry_count=0,
            )
            db.insert_song(song)
            new_songs.append(song)
        elif duration_secs > 0:
            existing = db.get_song(video_id)
            if existing is not None and existing.duration_secs == 0:
                db.update_song_duration(video_id, duration_secs)

    return new_songs
