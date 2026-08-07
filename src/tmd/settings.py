"""Application settings using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path
from tmd.config import get_music_dir


class Settings(BaseSettings):
    """TMD application settings."""

    model_config = SettingsConfigDict(
        env_prefix="TMD_",
        env_file="~/.config/tmd/.env",
        env_file_encoding="utf-8",
    )

    audio_quality: str = Field(default="192k", pattern=r"^(128k|192k|256k|320k)$")
    download_dir: Path = Field(default_factory=get_music_dir)
    max_concurrent_downloads: int = Field(default=2, ge=1, le=5)
    visualizer_bars: int = Field(default=32, ge=16, le=64)
    visualizer_fps: int = Field(default=30, ge=15, le=60)

    # YouTube Data API
    youtube_api_key: str = Field(default="")
    youtube_client_id: str = Field(default="")
    youtube_client_secret: str = Field(default="")

    def save(self, path: Path) -> None:
        """Save settings to JSON file."""
        import json

        data = self.model_dump()
        # Convert Path to string for JSON serialization
        data["download_dir"] = str(data["download_dir"])
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path) -> "Settings":
        """Load settings from JSON file."""
        import json

        if not path.exists():
            return cls()
        data = json.loads(path.read_text())
        if "download_dir" in data:
            data["download_dir"] = Path(data["download_dir"])
        return cls(**data)
