"""Google OAuth2 authentication."""

import os
import json
from typing import Optional

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from tmd.config import get_credentials_path


# Scopes needed for YouTube Data API
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def _build_client_config(client_id: str, client_secret: str) -> dict:
    """Build client config dict matching Google Cloud Console download format."""
    return {
        "installed": {
            "client_id": client_id,
            "project_id": "",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost:8080"],
        }
    }


def authenticate(client_id: str, client_secret: str) -> Credentials:
    """Run OAuth2 flow and return credentials.

    Uses google-auth-oauthlib's built-in run_local_server() which handles:
    - redirect_uri inclusion in auth URL
    - browser opening
    - local callback server
    - token exchange
    """
    client_config = _build_client_config(client_id, client_secret)
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

    # run_local_server handles everything: auth URL, browser, callback, token exchange
    creds = flow.run_local_server(
        port=8080,
        prompt="consent",
        success_message="Authentication successful! You can close this window.",
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
