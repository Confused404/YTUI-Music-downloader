## MODIFIED Requirements

### Requirement: Tiered music-only filter
The system SHALL evaluate liked videos through a 5-pass tiered filter. The system SHALL process passes in strict priority order, with earlier passes acting as fast acceptance (channel whitelist) or fast rejection (title keywords, category blacklist). The system SHALL only reach later, more ambiguous passes if earlier passes did not produce a definitive result.

#### Scenario: Priority order
- **GIVEN** a liked video
- **WHEN** the filter is enabled
- **THEN** the system evaluates in this order:
  1. **Accept if** channel name contains VEVO or " - Topic"
  2. **Reject if** title contains non-music keywords (trailer, review, tutorial, vlog, podcast, how to, walkthrough, unboxing, reaction, compilation, highlights, news, interview, documentary, gameplay, lets play, live stream, asmr, cooking, recipe, workout, fitness, meditation, stand-up, comedy special, full special)
  3. **Reject if** category ID is in the non-music blacklist (17=Sports, 20=Gaming, 22=People & Blogs, 25=News & Politics, 27=Education, 28=Science & Technology)
  4. **Accept if** categoryId is "10" (Music) AND duration is 60–600 seconds
  5. **Accept if** duration is 60–600 seconds AND title contains " - "
  6. **Otherwise reject**

---

### Requirement: Channel name music whitelist
The system SHALL identify music content by checking if the video's channel name contains known music markers. The system SHALL NOT use generic terms like "official" or "music" as markers due to high false-positive rates.

#### Scenario: VEVO channel
- **WHEN** a liked video's channel title contains "vevo" (case-insensitive)
- **THEN** the system classifies it as music and includes it in sync

#### Scenario: Topic channel
- **WHEN** a liked video's channel title contains " - topic" (case-insensitive)
- **THEN** the system classifies it as music and includes it in sync

#### Scenario: VEVO channel in blacklisted category
- **WHEN** a liked video's channel title contains "vevo"
- **AND** its category ID is in the non-music blacklist (e.g., 17=Sports)
- **THEN** the channel whitelist SHALL take precedence and the system classifies it as music

#### Scenario: Non-music channel with "official" in name
- **WHEN** a liked video's channel title is "Programming Official"
- **AND** "official" is not a reliable music marker
- **THEN** the system proceeds to Pass 2–5 evaluation (does not auto-accept)

#### Scenario: Non-music channel with "music" in name
- **WHEN** a liked video's channel title is "Sports Music Channel"
- **AND** "music" is not a reliable music marker
- **THEN** the system proceeds to Pass 2–5 evaluation (does not auto-accept)

---

### Requirement: Title keyword blacklist (early rejection)
The system SHALL reject videos whose titles contain keywords strongly associated with non-music content, regardless of other signals.

#### Scenario: Movie trailer with hyphen in title
- **WHEN** a video has duration `PT2M30S` (150 seconds)
- **AND** its title is "Marvel - Avengers Trailer"
- **AND** the title contains the non-music keyword "trailer"
- **THEN** the system rejects it at Pass 2, regardless of duration or title pattern

#### Scenario: Podcast with non-music keywords
- **WHEN** a video has duration `PT5M30S` (330 seconds)
- **AND** its title is "My Podcast Episode 42"
- **AND** the title contains the non-music keyword "podcast"
- **THEN** the system rejects it at Pass 2, regardless of duration

#### Scenario: Vlog in title
- **WHEN** a video's title is "My Day - Vlog #42"
- **AND** the title contains the non-music keyword "vlog"
- **THEN** the system rejects it at Pass 2

#### Scenario: Gaming tutorial in title
- **WHEN** a video's title is "Minecraft - How to Build a House"
- **AND** the title contains the non-music keyword "how to"
- **THEN** the system rejects it at Pass 2

---

### Requirement: YouTube category ID blacklist (early rejection)
The system SHALL reject videos whose category ID indicates content types virtually never associated with music. This pass applies only to videos not already accepted by the channel whitelist.

#### Scenario: Sports highlight
- **WHEN** a liked video's category ID is "17" (Sports)
- **AND** its title is "NBA - Best Dunks 2024"
- **AND** it did not pass the channel whitelist
- **THEN** the system rejects it at Pass 3, regardless of duration or title pattern

#### Scenario: Gaming video
- **WHEN** a liked video's category ID is "20" (Gaming)
- **AND** its title is "Game Soundtrack - Level 1"
- **AND** it did not pass the channel whitelist
- **THEN** the system rejects it at Pass 3
- **NOTE** A legitimate music video uploaded by a gaming channel but on VEVO would pass at Pass 1

#### Scenario: Education tutorial
- **WHEN** a liked video's category ID is "27" (Education)
- **AND** its title is "Python - How to Code"
- **AND** it did not pass the channel whitelist
- **THEN** the system rejects it at Pass 3

---

### Requirement: YouTube category ID filter (Music category)
The system SHALL classify content as music if its YouTube `categoryId` is `"10"` (Music category) AND its duration is within the music range (60–600 seconds).

#### Scenario: Music category video within duration range
- **WHEN** a video's `categoryId` is `"10"`
- **AND** its duration is between 60–600 seconds
- **AND** it was not rejected by earlier passes
- **THEN** the system classifies it as music and includes it in sync

#### Scenario: Miscategorized news video (false positive prevention)
- **WHEN** a video's `categoryId` is `"10"` (wrongly categorized by YouTube)
- **AND** its title contains non-music keywords like "news" or "breaking"
- **THEN** the system rejects it at Pass 2 before reaching Pass 4

#### Scenario: Long music mix failing duration gate
- **WHEN** a video's `categoryId` is `"10"`
- **AND** its duration is `PT1H30M` (5400 seconds)
- **AND** it was not rejected by earlier passes
- **THEN** the system rejects it at Pass 4 because duration exceeds 600 seconds
- **RATIONALE** Prevents livestreams, DJ sets, and album-length content from passing via category alone

#### Scenario: Short song intro failing duration gate
- **WHEN** a video's `categoryId` is `"10"`
- **AND** its duration is `PT30S` (30 seconds)
- **AND** it was not rejected by earlier passes
- **THEN** the system rejects it at Pass 4 because duration is below 60 seconds
- **RATIONALE** Prevents intro clips, skits, and non-song content from passing via category alone

---

### Requirement: Duration and title pattern filter (fallback)
The system SHALL classify ambiguous content as music if its duration is between 60–600 seconds AND its title contains `" - "`. This is the final pass and only reachable if all earlier passes were inconclusive or non-blocking.

#### Scenario: Indie song matching pattern
- **WHEN** a video has duration `PT4M12S` (252 seconds)
- **AND** its title is "Unknown Artist - Great Song"
- **AND** it was not accepted or rejected by earlier passes
- **THEN** the system classifies it as music and includes it in sync

#### Scenario: Ambiguous title without hyphen
- **WHEN** a video has duration `PT3M30S` (210 seconds)
- **AND** its title is "Great Song"
- **AND** it did not pass earlier heuristics
- **THEN** the system classifies it as non-music and excludes it from sync

#### Scenario: Long mix failing duration gate
- **WHEN** a video has duration `PT1H15M` (4500 seconds)
- **AND** its title is "DJ Mix - Best of 2024"
- **AND** it did not pass earlier heuristics
- **THEN** the system classifies it as non-music and excludes it from sync

---

### Requirement: Configurable filter toggle
The system SHALL allow the music filter to be enabled or disabled via a parameter.

#### Scenario: Filter enabled (default)
- **WHEN** `sync_liked_songs()` is called with `filter_music_only=True`
- **THEN** only items classified as music are synced

#### Scenario: Filter disabled
- **WHEN** `sync_liked_songs()` is called with `filter_music_only=False`
- **THEN** all liked videos are synced regardless of content type
- **AND** no filter evaluation is performed
