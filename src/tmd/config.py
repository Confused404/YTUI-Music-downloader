"""Configuration directory helpers."""

import os
from pathlib import Path


def get_config_dir() -> Path:
    """Return the TMD config directory ( ~/.config/tmd/ )."""
    config_dir = Path.home() / ".config" / "tmd"
    config_dir.mkdir(parents=True, exist_ok=True)
    # Ensure restrictive permissions: rwx------
    os.chmod(config_dir, 0o700)
    return config_dir


def get_data_dir() -> Path:
    """Return the TMD data directory ( ~/.local/share/tmd/ )."""
    data_dir = Path.home() / ".local" / "share" / "tmd"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_music_dir() -> Path:
    """Return the default music download directory ( ~/Music/liked-songs/ )."""
    music_dir = Path.home() / "Music" / "liked-songs"
    music_dir.mkdir(parents=True, exist_ok=True)
    return music_dir


def get_credentials_path() -> Path:
    """Return the path to the OAuth2 credentials file."""
    return get_config_dir() / "credentials.json"


def get_settings_path() -> Path:
    """Return the path to the settings JSON file."""
    return get_config_dir() / "settings.json"


def get_database_path() -> Path:
    """Return the path to the SQLite database file."""
    return get_data_dir() / "library.db"
