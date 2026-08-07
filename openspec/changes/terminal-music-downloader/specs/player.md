## ADDED Requirements

### Requirement: Decode MP3 to raw PCM
The system SHALL decode MP3 files into raw float32 PCM buffers suitable for playback and analysis.

#### Scenario: Load song for playback
- **WHEN** the user selects a song to play
- **THEN** the system loads the MP3 file using librosa at the native sample rate
- **AND** stores the full PCM array in memory for sequential playback

### Requirement: Stream audio via sounddevice
The system SHALL play decoded PCM audio through the system speakers using a callback-based audio stream.

#### Scenario: Start playback
- **WHEN** the user presses Play or Enter on a song
- **THEN** the system opens a sounddevice OutputStream with the MP3's sample rate
- **AND** begins feeding PCM chunks to the stream in a background thread
- **AND** the stream runs until the song ends or the user stops it

### Requirement: Real-time FFT frequency analysis
The system SHALL perform Fast Fourier Transform on the currently playing audio buffer to produce a frequency spectrum.

#### Scenario: FFT during playback
- **WHEN** the audio player feeds a chunk to the output stream
- **THEN** the system applies a Hann window to a 1024-sample buffer
- **AND** computes numpy.fft.rfft to produce complex frequency bins
- **AND** calculates log-scaled magnitude for each bin
- **AND** aggregates bins into 32 frequency bars spaced logarithmically from 20Hz to 20kHz

### Requirement: Render FFT visualizer on Textual Canvas
The system SHALL draw the frequency spectrum as animated bars on a Textual Canvas widget.

#### Scenario: Visualizer rendering
- **WHEN** new FFT data is available (target 30-60 FPS)
- **THEN** the visualizer widget clears the canvas
- **AND** draws 32 vertical bars using Unicode block characters (█ ▉ ▊ ▋ ▌ ▍ ▎ ▏)
- **AND** scales bar height proportionally to frequency magnitude
- **AND** applies a gradient color scheme (e.g., green low → yellow mid → red high)
- **AND** refreshes the canvas display

### Requirement: Playback controls
The system SHALL provide standard playback controls accessible via keyboard.

#### Scenario: User controls playback
- **WHEN** the user presses Space
- **THEN** playback toggles between play and pause
- **WHEN** the user presses n or Right Arrow
- **THEN** playback skips to the next song in the library
- **WHEN** the user presses p or Left Arrow
- **THEN** playback returns to the previous song
- **WHEN** the user presses + or -
- **THEN** volume increases or decreases by 10%
