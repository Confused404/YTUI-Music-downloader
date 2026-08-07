"""Audio player with real-time FFT visualizer."""

import numpy as np
import sounddevice as sd
import librosa
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum, auto


class PlaybackState(Enum):
    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()


@dataclass
class VisualizerData:
    bars: np.ndarray  # 32 frequency bar heights (0-1 normalized)
    peak: float


class AudioPlayer:
    """Plays MP3 files with real-time FFT visualizer output."""

    def __init__(
        self,
        visualizer_callback: Optional[Callable[[VisualizerData], None]] = None,
        num_bars: int = 32,
        fps: int = 30,
    ):
        self.visualizer_callback = visualizer_callback
        self.num_bars = num_bars
        self.fps = fps
        self.chunk_size = 1024
        self._state = PlaybackState.STOPPED
        self._audio_data: Optional[np.ndarray] = None
        self._sample_rate: int = 44100
        self._position: int = 0
        self._stream: Optional[sd.OutputStream] = None
        self._volume: float = 1.0
        self._song_duration: float = 0.0

    def load(self, file_path: Path) -> bool:
        """Load an MP3 file into memory."""
        try:
            self._audio_data, self._sample_rate = librosa.load(
                str(file_path), sr=None, mono=True
            )
            self._song_duration = librosa.get_duration(
                y=self._audio_data, sr=self._sample_rate
            )
            self._position = 0
            return True
        except Exception:
            return False

    def _audio_callback(
        self, outdata: np.ndarray, frames: int, time_info, status
    ) -> None:
        """Sounddevice callback - fills audio buffer and computes FFT."""
        if self._state != PlaybackState.PLAYING or self._audio_data is None:
            outdata.fill(0)
            return

        end_pos = self._position + frames
        if end_pos > len(self._audio_data):
            # Reached end of song
            remaining = len(self._audio_data) - self._position
            if remaining > 0:
                outdata[:remaining, 0] = (
                    self._audio_data[self._position :] * self._volume
                )
            outdata[remaining:, 0] = 0
            self._position = 0
            self._state = PlaybackState.STOPPED
        else:
            chunk = self._audio_data[self._position : end_pos] * self._volume
            outdata[:, 0] = chunk
            self._position = end_pos

            # Compute FFT for visualizer
            if self.visualizer_callback and len(chunk) >= self.chunk_size:
                self._compute_fft(chunk[-self.chunk_size :])

        # Fill all channels (mono -> stereo)
        if outdata.shape[1] > 1:
            outdata[:, 1] = outdata[:, 0]

    def _compute_fft(self, chunk: np.ndarray) -> None:
        """Compute FFT and emit visualizer data."""
        # Apply Hann window
        window = np.hanning(len(chunk))
        windowed = chunk * window

        # FFT
        fft = np.fft.rfft(windowed)
        magnitude = np.abs(fft)

        # Convert to log scale and normalize
        magnitude = np.log1p(magnitude)

        # Aggregate into log-spaced frequency bins
        freqs = np.fft.rfftfreq(len(chunk), 1.0 / self._sample_rate)
        bars = np.zeros(self.num_bars)

        # Log-spaced bin edges from 20Hz to Nyquist
        log_edges = np.logspace(
            np.log10(20), np.log10(self._sample_rate / 2), self.num_bars + 1
        )

        for i in range(self.num_bars):
            mask = (freqs >= log_edges[i]) & (freqs < log_edges[i + 1])
            if np.any(mask):
                bars[i] = np.mean(magnitude[mask])

        # Normalize
        max_val = np.max(bars)
        if max_val > 0:
            bars = bars / max_val

        visualizer = VisualizerData(bars=bars, peak=np.max(bars))
        self.visualizer_callback(visualizer)

    def play(self) -> None:
        """Start or resume playback."""
        if self._audio_data is None:
            return

        if self._state == PlaybackState.PAUSED:
            self._state = PlaybackState.PLAYING
            return

        self._state = PlaybackState.PLAYING
        self._stream = sd.OutputStream(
            samplerate=self._sample_rate,
            channels=2,
            dtype=np.float32,
            blocksize=self.chunk_size,
            callback=self._audio_callback,
        )
        self._stream.start()

    def pause(self) -> None:
        """Pause playback."""
        if self._state == PlaybackState.PLAYING:
            self._state = PlaybackState.PAUSED

    def stop(self) -> None:
        """Stop playback and reset position."""
        self._state = PlaybackState.STOPPED
        self._position = 0
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def toggle_playback(self) -> None:
        """Toggle between play and pause."""
        if self._state == PlaybackState.PLAYING:
            self.pause()
        else:
            self.play()

    def seek(self, position: float) -> None:
        """Seek to a position in seconds."""
        if self._audio_data is not None:
            self._position = int(position * self._sample_rate)
            self._position = max(0, min(self._position, len(self._audio_data)))

    @property
    def current_position(self) -> float:
        """Current playback position in seconds."""
        if self._audio_data is None:
            return 0.0
        return self._position / self._sample_rate

    @property
    def duration(self) -> float:
        """Total song duration in seconds."""
        return self._song_duration

    @property
    def state(self) -> PlaybackState:
        """Current playback state."""
        return self._state

    @property
    def volume(self) -> float:
        return self._volume

    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0+)."""
        self._volume = max(0.0, min(2.0, volume))

    def volume_up(self) -> None:
        """Increase volume by 10%."""
        self.set_volume(self._volume + 0.1)

    def volume_down(self) -> None:
        """Decrease volume by 10%."""
        self.set_volume(self._volume - 0.1)
