"""Google OAuth2 authentication with manual PKCE flow."""

import os
import json
import base64
import hashlib
import secrets
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
from typing import Optional
import requests

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError

from tmd.config import get_credentials_path


# Scopes needed for YouTube Data API
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REDIRECT_URI = "http://localhost:8080"


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


def _generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge."""
    # 43-128 chars of unreserved characters
    verifier = base64.urlsafe_b64encode(
        secrets.token_bytes(64)
    ).decode("ascii").rstrip("=")
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).decode("ascii").rstrip("=")
    return verifier, challenge


def validate_credentials(client_id: str, client_secret: str) -> None:
    """Validate that OAuth credentials are configured."""
    if not client_id or not client_secret:
        raise AuthenticationError(
            "Google OAuth2 credentials not configured.\n\n"
            "Please set one of the following:\n"
            "1. Environment variables: TMD_YOUTUBE_CLIENT_ID and TMD_YOUTUBE_CLIENT_SECRET\n"
            "2. Or edit ~/.config/tmd/settings.json and add:\n"
            '   {"youtube_client_id": "your-id", "youtube_client_secret": "your-secret"}\n\n'
            "Get your credentials from: https://console.cloud.google.com/apis/credentials"
        )


def authenticate(client_id: str, client_secret: str) -> Credentials:
    """Run OAuth2 flow with PKCE and return credentials."""
    validate_credentials(client_id, client_secret)
    
    # Generate PKCE
    code_verifier, code_challenge = _generate_pkce()

    # Build authorization URL with ALL required parameters
    auth_params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{AUTH_URL}?{urlencode(auth_params)}"

    # Start local redirect server
    server = HTTPServer(("localhost", 8080), _RedirectHandler)
    server.auth_code = None
    server.auth_error = None

    # Open browser
    webbrowser.open(auth_url)

    # Wait for callback
    server.handle_request()
    server.server_close()

    if server.auth_error:
        raise AuthenticationError(f"OAuth error: {server.auth_error}")
    if not server.auth_code:
        raise AuthenticationError("No authorization code received")

    # Exchange code for tokens
    token_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": server.auth_code,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
    }

    response = requests.post(TOKEN_URL, data=token_data)
    if response.status_code != 200:
        raise AuthenticationError(f"Token exchange failed: {response.text}")

    token_info = response.json()

    creds = Credentials(
        token=token_info["access_token"],
        refresh_token=token_info.get("refresh_token"),
        token_uri=TOKEN_URL,
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

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
        try:
            creds.refresh(Request())
            save_credentials(creds)
        except RefreshError as e:
            if "invalid_grant" in str(e):
                # Token expired or revoked — clean up and prompt re-auth
                logout()
                raise TokenExpiredError(
                    "Your session expired. Please sign in again."
                ) from e
            # Other refresh errors (network, etc.) propagate normally
            raise AuthenticationError(f"Token refresh failed: {e}") from e

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


class TokenExpiredError(AuthenticationError):
    """Raised when the refresh token has expired or been revoked."""
    pass
