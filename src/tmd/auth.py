"""Google OAuth2 authentication."""

import os
import json
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from tmd.config import get_config_dir, get_credentials_path


# Scopes needed for YouTube Data API
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


class _RedirectHandler(BaseHTTPRequestHandler):
    """Handles OAuth2 redirect callback."""

    def do_GET(self):
        """Capture authorization code from redirect."""
        query = parse_qs(urlparse(self.path).query)
        self.server.auth_code = query.get("code", [None])[0]
        self.server.auth_error = query.get("error", [None])[0]

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        if self.server.auth_code:
            self.wfile.write(
                b"<h1>Authentication successful!</h1><p>You can close this window.</p>"
            )
        else:
            self.wfile.write(
                b"<h1>Authentication failed.</h1><p>Please try again.</p>"
            )

    def log_message(self, format, *args):
        """Suppress server logs."""
        pass


def authenticate(client_id: str, client_secret: str) -> Credentials:
    """Run OAuth2 flow and return credentials."""
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8080"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

    # Use local server on port 8080
    server = HTTPServer(("localhost", 8080), _RedirectHandler)
    server.auth_code = None
    server.auth_error = None

    # Get authorization URL
    auth_url, _ = flow.authorization_url(prompt="consent")

    # Open browser
    webbrowser.open(auth_url)

    # Wait for callback
    server.handle_request()
    server.server_close()

    if server.auth_error:
        raise AuthenticationError(f"OAuth error: {server.auth_error}")
    if not server.auth_code:
        raise AuthenticationError("No authorization code received")

    flow.fetch_token(code=server.auth_code)
    creds = flow.credentials

    # Save with restricted permissions
    save_credentials(creds)
    return creds


def save_credentials(creds: Credentials) -> None:
    """Save credentials to file with 600 permissions."""
    creds_path = get_credentials_path()
    creds_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }
    creds_path.write_text(json.dumps(creds_data))
    os.chmod(creds_path, 0o600)


def load_credentials() -> Optional[Credentials]:
    """Load credentials from file if they exist."""
    creds_path = get_credentials_path()
    if not creds_path.exists():
        return None

    creds_data = json.loads(creds_path.read_text())
    creds = Credentials(**creds_data)

    # Refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        save_credentials(creds)

    return creds


def is_authenticated() -> bool:
    """Check if valid credentials exist."""
    creds = load_credentials()
    return creds is not None and creds.valid


def logout() -> None:
    """Delete stored credentials."""
    creds_path = get_credentials_path()
    if creds_path.exists():
        creds_path.unlink()


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass
