"""YouTube search module."""

from typing import List, Dict, Any
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


def search_youtube(creds: Credentials, query: str, max_results: int = 25) -> List[Dict[str, Any]]:
    """Search YouTube for videos matching the query."""
    youtube = build("youtube", "v3", credentials=creds)

    request = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=max_results,
    )
    response = request.execute()

    results = []
    for item in response["items"]:
        snippet = item["snippet"]
        results.append({
            "video_id": item["id"]["videoId"],
            "title": snippet["title"],
            "artist": snippet.get("channelTitle", "Unknown"),
            "published_at": snippet["publishedAt"],
            "thumbnail": snippet["thumbnails"]["default"]["url"],
        })

    return results


def add_to_liked_playlist(creds: Credentials, video_id: str) -> bool:
    """Add a video to the user's liked playlist."""
    youtube = build("youtube", "v3", credentials=creds)

    try:
        request = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": "LL",
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id,
                    }
                }
            }
        )
        request.execute()
        return True
    except Exception:
        return False
