#!/usr/bin/env python3
"""CLI entry point to launch the GTA V HUB • Los Santos Network Catalogue API server."""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from gta_hub.api.server import run_server


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="GTA V HUB • Los Santos Network First-Party Catalogue API Server"
    )
    parser.add_argument(
        "--host",
        default=os.getenv("CATALOGUE_API_HOST", "127.0.0.1"),
        help="Host interface to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("CATALOGUE_API_PORT", "8080")),
        help="Port to listen on (default: 8080)",
    )
    parser.add_argument(
        "--data-dir",
        default=os.getenv("DATA_DIR", "data"),
        help="Path to catalogue data directory (default: data)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    run_server(host=args.host, port=args.port, data_dir=Path(args.data_dir))


if __name__ == "__main__":
    main()

