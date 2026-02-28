from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a SQLite database to a portable SQL dump.")
    parser.add_argument(
        "--db",
        dest="db_path",
        default="instance/smartcourse.db",
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--out",
        dest="output_path",
        default="instance/smartcourse_dump.sql",
        help="Path to write the SQL dump.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db_path)
    output_path = Path(args.output_path)

    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as connection, output_path.open("w", encoding="utf-8") as handle:
        for statement in connection.iterdump():
            handle.write(statement)
            handle.write("\n")

    print(f"Exported SQL dump to {output_path}")


if __name__ == "__main__":
    main()
