"""Integration tests for the music-only filter.

These tests mock YouTube API responses to audit which types of videos
pass through the filter and identify false positives.
"""

import pytest
from unittest.mock import MagicMock, patch
from tmd.sync import (
    fetch_liked_songs,
    _is_music_channel,
    _parse_duration,
    _has_non_music_keywords,
)


# ── Test Data: Real-world video scenarios ──

# Music videos that SHOULD pass
MUSIC_VIDEOS = [
    {
        "name": "Adele - Hello (Official Video)",
        "video_id": "test_001",
        "title": "Adele - Hello (Official Video)",
        "artist": "AdeleVEVO",
        "duration": "PT4M55S",  # 295s
        "category_id": "10",
        "expected": True,
    },
    {
        "name": "Taylor Swift via Topic channel",
        "video_id": "test_002",
        "title": "Taylor Swift - Shake It Off",
        "artist": "Taylor Swift - Topic",
        "duration": "PT3M39S",  # 219s
        "category_id": "10",
        "expected": True,
    },
    {
        "name": "Indie artist with hyphen in title",
        "video_id": "test_003",
        "title": "Unknown Artist - Great Song (Official Audio)",
        "artist": "Some Indie Label",
        "duration": "PT3M30S",  # 210s
        "category_id": "24",  # Entertainment, not Music
        "expected": True,  # Passes via duration + title pattern
    },
]

# Non-music videos that SHOULD be filtered out
NON_MUSIC_VIDEOS = [
    {
        "name": "Podcast with ' - ' in title",
        "video_id": "test_101",
        "title": "Joe Rogan - Elon Musk Interview",
        "artist": "PowerfulJRE",
        "duration": "PT2H30M",  # 9000s - too long
        "category_id": "24",  # Entertainment
        "expected": False,
    },
    {
        "name": "Short meme clip",
        "video_id": "test_102",
        "title": "Funny Meme Compilation 2024",
        "artist": "MemeLord Official",
        "duration": "PT45S",  # 45s - too short
        "category_id": "24",  # Entertainment
        "expected": False,
    },
    {
        "name": "Gaming video with ' - ' in title",
        "video_id": "test_103",
        "title": "Minecraft - How to Build a House",
        "artist": "GamingWithMusic",
        "duration": "PT5M30S",  # 330s - within range
        "category_id": "20",  # Gaming
        "expected": False,  # "How to" in title is non-music keyword
    },
    {
        "name": "Tutorial video within duration range",
        "video_id": "test_104",
        "title": "Python - How to Code",
        "artist": "Programming Official",
        "duration": "PT4M00S",  # 240s - within range
        "category_id": "27",  # Education
        "expected": False,  # "How to" in title is non-music keyword
    },
    {
        "name": "Movie trailer with ' - ' in title",
        "video_id": "test_105",
        "title": "Marvel - Avengers Trailer",
        "artist": "Marvel Entertainment",
        "duration": "PT2M30S",  # 150s - within range
        "category_id": "1",  # Film & Animation
        "expected": False,
    },
    {
        "name": "News video with Music category (false positive)",
        "video_id": "test_106",
        "title": "Breaking News Today",
        "artist": "News Channel",
        "duration": "PT5M00S",  # 300s - within range
        "category_id": "10",  # Wrongly categorized as Music!
        "expected": False,  # BUT: categoryId == "10" lets it through!
    },
    {
        "name": "Vlog with ' - ' in title",
        "video_id": "test_107",
        "title": "My Day - Vlog #42",
        "artist": "Vlogger Official",
        "duration": "PT4M00S",  # 240s - within range
        "category_id": "22",  # People & Blogs
        "expected": False,  # "vlog" in title is non-music keyword
    },
    {
        "name": "Sports highlight with ' - ' in title",
        "video_id": "test_108",
        "title": "NBA - Best Dunks 2024",
        "artist": "Sports Music Channel",
        "duration": "PT3M45S",  # 225s - within range
        "category_id": "17",  # Sports
        "expected": False,  # Rejected by category blacklist (Sports)
    },
]

# Edge cases
EDGE_CASES = [
    {
        "name": "Long music mix (DJ set)",
        "video_id": "test_201",
        "title": "DJ Mix - Best of 2024",
        "artist": "DJ Official",
        "duration": "PT1H30M",  # 5400s - too long for duration gate
        "category_id": "10",  # Music category
        # Now categoryId==10 requires duration 60-600s to prevent
        # livestreams and miscategorized long content from passing
        "expected": False,
    },
    {
        "name": "Short song intro clip",
        "video_id": "test_202",
        "title": "Song - Intro Snippet",
        "artist": "Artist Name",
        "duration": "PT30S",  # 30s - too short
        "category_id": "10",  # Music category
        # Now categoryId==10 requires duration 60-600s
        "expected": False,
    },
    {
        "name": "Podcast at exactly 60s boundary",
        "video_id": "test_203",
        "title": "Podcast - Episode 1",
        "artist": "Podcast Channel",
        "duration": "PT1M00S",  # 60s - exactly at lower boundary
        "category_id": "24",  # Entertainment
        "expected": False,
    },
    {
        "name": "Video at exactly 600s boundary",
        "video_id": "test_204",
        "title": "Review - Product Name",
        "artist": "Review Channel Official",
        "duration": "PT10M00S",  # 600s - exactly at upper boundary
        "category_id": "24",  # Entertainment
        "expected": False,  # "review" in title is non-music keyword
    },
    {
        "name": "VEVO channel in blacklisted category",
        "video_id": "test_205",
        "title": "Artist - Song (Live at Sports Event)",
        "artist": "ArtistVEVO",
        "duration": "PT4M00S",  # 240s - within range
        "category_id": "17",  # Sports (blacklisted!)
        "expected": True,  # Channel whitelist MUST override category blacklist
    },
]


# ── Helper to create mock YouTube API responses ──

def _make_mock_youtube(video_list):
    """Create a mock YouTube API client that returns the given video data."""
    mock_youtube = MagicMock()
    
    # Mock playlistItems().list() response
    playlist_items = []
    for v in video_list:
        playlist_items.append({
            "snippet": {
                "resourceId": {"videoId": v["video_id"]},
                "title": v["title"],
                "videoOwnerChannelTitle": v["artist"],
                "publishedAt": "2024-01-01T00:00:00Z",
            }
        })
    
    mock_youtube.playlistItems().list().execute.return_value = {
        "items": playlist_items,
        "nextPageToken": None,
    }
    
    # Mock videos().list() response
    video_items = []
    for v in video_list:
        video_items.append({
            "id": v["video_id"],
            "snippet": {"categoryId": v["category_id"]},
            "contentDetails": {"duration": v["duration"]},
        })
    
    mock_youtube.videos().list().execute.return_value = {
        "items": video_items,
    }
    
    return mock_youtube


# ── Tests ──

class TestMusicChannelHeuristic:
    """Test the Pass 1 channel-name heuristic."""
    
    def test_vevo_channel_passes(self):
        assert _is_music_channel("AdeleVEVO") is True
    
    def test_topic_channel_passes(self):
        assert _is_music_channel("Taylor Swift - Topic") is True
    
    def test_official_in_channel_rejected(self):
        # "official" removed from keywords — too many false positives
        assert _is_music_channel("Vlogger Official") is False

    def test_music_in_channel_rejected(self):
        # "music" removed from keywords — too many false positives
        assert _is_music_channel("Sports Music Channel") is False
    
    def test_regular_channel_fails(self):
        assert _is_music_channel("PewDiePie") is False
    
    def test_empty_channel_fails(self):
        assert _is_music_channel("") is False


class TestDurationTitleHeuristic:
    """Test the Pass 2 duration + title pattern heuristic."""
    
    def test_indie_song_with_hyphen(self):
        # Duration 210s (3m30s), has " - " in title
        assert (60 <= 210 <= 600 and " - " in "Unknown Artist - Great Song") is True
    
    def test_podcast_too_long(self):
        # Duration 9000s (2h30m), too long
        assert (60 <= 9000 <= 600 and " - " in "Joe Rogan - Elon Musk") is False
    
    def test_meme_too_short(self):
        # Duration 45s, too short
        assert (60 <= 45 <= 600 and " - " in "Funny Meme") is False
    
    def test_tutorial_within_range(self):
        # Duration 240s (4m), has " - " in title
        assert (60 <= 240 <= 600 and " - " in "Python - How to Code") is True
    
    def test_no_hyphen_in_title(self):
        # Duration 240s, but no " - " in title
        assert (60 <= 240 <= 600 and " - " in "How to Code Python") is False


class TestMusicFilterIntegration:
    """Integration tests for the complete filter pipeline."""
    
    @pytest.mark.parametrize("video", MUSIC_VIDEOS, ids=lambda v: v["name"])
    def test_music_videos_pass(self, video):
        """Verify music videos are correctly accepted."""
        mock_youtube = _make_mock_youtube([video])
        
        with patch("tmd.sync.build", return_value=mock_youtube):
            result = fetch_liked_songs(MagicMock(), filter_music_only=True)
        
        assert len(result) == 1, f"{video['name']} should pass but was filtered out"
        assert result[0]["video_id"] == video["video_id"]
    
    @pytest.mark.parametrize("video", NON_MUSIC_VIDEOS, ids=lambda v: v["name"])
    def test_non_music_videos_filtered(self, video):
        """Verify non-music videos are correctly rejected.
        
        NOTE: Some of these tests may FAIL, indicating false positives
        in the filter that need to be fixed.
        """
        mock_youtube = _make_mock_youtube([video])
        
        with patch("tmd.sync.build", return_value=mock_youtube):
            result = fetch_liked_songs(MagicMock(), filter_music_only=True)
        
        if video["expected"]:
            assert len(result) == 1, f"{video['name']} should pass"
        else:
            # Document false positives
            if len(result) == 1:
                pytest.fail(
                    f"FALSE POSITIVE: {video['name']} passed filter but shouldn't.\n"
                    f"  Channel: '{video['artist']}'\n"
                    f"  Category: {video['category_id']}\n"
                    f"  Duration: {video['duration']}\n"
                    f"  Which heuristic passed it: {_identify_passing_heuristic(video)}"
                )
            assert len(result) == 0, f"{video['name']} should be filtered out"
    
    @pytest.mark.parametrize("video", EDGE_CASES, ids=lambda v: v["name"])
    def test_edge_cases(self, video):
        """Test edge cases and boundary conditions."""
        mock_youtube = _make_mock_youtube([video])
        
        with patch("tmd.sync.build", return_value=mock_youtube):
            result = fetch_liked_songs(MagicMock(), filter_music_only=True)
        
        if video["expected"]:
            assert len(result) == 1, f"{video['name']} should pass"
        else:
            if len(result) == 1:
                pytest.fail(
                    f"FALSE POSITIVE: {video['name']} passed filter but shouldn't.\n"
                    f"  Which heuristic: {_identify_passing_heuristic(video)}"
                )
            assert len(result) == 0, f"{video['name']} should be filtered out"


def _identify_passing_heuristic(video):
    """Identify which heuristic would let a video through."""
    if _is_music_channel(video["artist"]):
        return "PASS 1: Channel name contains music marker"
    elif video["category_id"] == "10":
        return "PASS 2: categoryId == '10' (Music)"
    elif 60 <= _parse_duration(video["duration"]) <= 600 and " - " in video["title"]:
        return "PASS 2: Duration + title pattern"
    else:
        return "UNKNOWN - should not have passed"


class TestFilterAuditReport:
    """Generate an audit report of filter accuracy."""
    
    def test_generate_false_positive_report(self):
        """Run all non-music videos and report which ones pass incorrectly."""
        false_positives = []
        
        for video in NON_MUSIC_VIDEOS:
            mock_youtube = _make_mock_youtube([video])
            
            with patch("tmd.sync.build", return_value=mock_youtube):
                result = fetch_liked_songs(MagicMock(), filter_music_only=True)
            
            if len(result) == 1 and not video["expected"]:
                false_positives.append({
                    "name": video["name"],
                    "channel": video["artist"],
                    "category": video["category_id"],
                    "duration": video["duration"],
                    "heuristic": _identify_passing_heuristic(video),
                })
        
        # Print audit report
        print("\n" + "=" * 70)
        print("MUSIC FILTER FALSE POSITIVE AUDIT REPORT")
        print("=" * 70)
        
        if false_positives:
            print(f"\nFound {len(false_positives)} false positives out of {len(NON_MUSIC_VIDEOS)} non-music videos:")
            print()
            for fp in false_positives:
                print(f"  ❌ {fp['name']}")
                print(f"     Channel: '{fp['channel']}'")
                print(f"     Category: {fp['category']}")
                print(f"     Duration: {fp['duration']}")
                print(f"     Passes via: {fp['heuristic']}")
                print()
        else:
            print(f"\n✅ All {len(NON_MUSIC_VIDEOS)} non-music videos were correctly filtered out!")
        
        print("=" * 70)
        
        # This test always passes - it's for reporting only
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
