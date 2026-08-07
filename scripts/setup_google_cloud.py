#!/usr/bin/env python3
"""
Setup script to create Google Cloud project, enable YouTube API,
and create OAuth2 desktop client credentials.

Requires: google-auth, google-auth-oauthlib, google-api-python-client
"""

import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


def get_auth_code():
    """Capture OAuth2 auth code from browser redirect."""
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            self.server.code = query.get("code", [None])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Success! You can close this window.")
        def log_message(self, *args):
            pass

    server = HTTPServer(("localhost", 8085), Handler)
    server.code = None
    server.handle_request()
    server.server_close()
    return server.code


def main():
    print("=" * 60)
    print("TMD Google Cloud Setup")
    print("=" * 60)
    print()
    print("This script will:")
    print("  1. Open your browser to Google Cloud Console")
    print("  2. Guide you to create OAuth2 credentials")
    print()
    print("Please follow the browser instructions.")
    print()

    # Instructions URL
    setup_url = (
        "https://console.cloud.google.com/apis/credentials?"
        "project=tmd-setup&hl=en"
    )

    print(f"Opening: {setup_url}")
    webbrowser.open(setup_url)

    print()
    print("After creating your OAuth2 Desktop client:")
    client_id = input("Paste your Client ID: ").strip()
    client_secret = input("Paste your Client Secret: ").strip()

    if not client_id or not client_secret:
        print("Error: Both Client ID and Secret are required.")
        return 1

    # Save to settings file
    from pathlib import Path
    config_dir = Path.home() / ".config" / "tmd"
    config_dir.mkdir(parents=True, exist_ok=True)

    settings = {
        "audio_quality": "192k",
        "youtube_client_id": client_id,
        "youtube_client_secret": client_secret,
    }

    settings_path = config_dir / "settings.json"
    settings_path.write_text(json.dumps(settings, indent=2))
    print(f"\n✓ Settings saved to {settings_path}")
    print(f"  Client ID: {client_id[:20]}...")
    print()
    print("You can now run: uv run tmd")
    return 0


if __name__ == "__main__":
    exit(main())
