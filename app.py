from __future__ import annotations

import argparse
import os

from smartcourse import create_app

app = create_app()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the SmartCourse Flask application.")
    parser.add_argument("--host", default=os.environ.get("SMARTCOURSE_HOST", "127.0.0.1"), help="Host interface.")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("SMARTCOURSE_PORT", "5000")),
        help="HTTP port.",
    )
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode.")
    parser.add_argument("--no-debug", action="store_true", help="Disable Flask debug mode.")
    return parser.parse_args()


def resolve_debug(args: argparse.Namespace) -> bool:
    if args.debug and args.no_debug:
        raise ValueError("Use either --debug or --no-debug, not both.")
    if args.debug:
        return True
    if args.no_debug:
        return False
    return os.environ.get("SMARTCOURSE_DEBUG", "1").strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    cli_args = parse_args()
    app.run(host=cli_args.host, port=cli_args.port, debug=resolve_debug(cli_args))
