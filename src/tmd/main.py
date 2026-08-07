"""Entry point for the Terminal Music Downloader."""

import sys
from tmd.tui_app import TMDApp


def main() -> int:
    """Run the TMD application."""
    app = TMDApp()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
