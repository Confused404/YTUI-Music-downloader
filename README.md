# Terminal Music Downloader (TMD)

A modern, terminal-based music downloader and player for YouTube Music liked songs. Features automatic sync, background downloading, and a real-time FFT audio visualizer.

## Features

- **Google OAuth2 Authentication** - Securely connect your Google account
- **Automatic Sync** - Fetches your YouTube Music liked songs on startup
- **Background Downloads** - Automatically downloads new liked songs via yt-dlp
- **YouTube Search** - Search for songs and add them to your liked playlist
- **Real-time Visualizer** - FFT frequency analyzer with Unicode block rendering
- **Modern TUI** - Built with Textual for a stunning terminal interface

## Installation

### Prerequisites

1. Python 3.11+
2. [uv](https://github.com/astral-sh/uv) (recommended) or `pip`
3. Google Cloud OAuth2 credentials (see setup below)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/Confused404/music-downloader-tui.git
cd music-downloader-tui
```

2. **Using uv** (recommended - fast, modern package manager):
```bash
uv venv .venv --python python3
uv pip install -e .
```

   **Using pip** (traditional):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

3. Set up Google OAuth2:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing
   - Enable the **YouTube Data API v3**
   - Go to **Credentials** → **Create Credentials** → **OAuth client ID**
   - Select **Desktop app** as application type
   - Download the client credentials JSON
   - Set environment variables:
```bash
export TMD_YOUTUBE_CLIENT_ID="your-client-id"
export TMD_YOUTUBE_CLIENT_SECRET="your-client-secret"
```

## Usage

### Running the App

**With uv** (recommended):
```bash
uv run tmd
```

**With pip/venv**:
```bash
source .venv/bin/activate
tmd
```

### Keybindings

| Key | Action |
|-----|--------|
| `Enter` | Play selected song |
| `Space` | Play/Pause |
| `n` | Next song |
| `p` | Previous song |
| `/` | Open search |
| `,` | Open settings |
| `q` | Quit |

### Search Screen

1. Press `/` to open search
2. Type your query and press Enter
3. Click a result to preview in browser
4. Press `d` to download and add to liked songs

### Settings

- **Audio Quality**: 128k, 192k, 256k, or 320k MP3
- **Download Directory**: Defaults to `~/Music/liked-songs/`
- **Logout**: Clears stored credentials

## Architecture

```
src/tmd/
├── __init__.py      # Package init
├── main.py          # Entry point
├── config.py        # Directory helpers
├── settings.py      # Pydantic settings
├── database.py      # SQLite library
├── auth.py          # Google OAuth2
├── sync.py          # YouTube sync
├── download.py      # yt-dlp manager
├── search.py        # YouTube search
├── player.py        # Audio + visualizer
└── tui_app.py       # Textual application
```

## License

MIT License
