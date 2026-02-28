from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


MAX_MB_DEFAULT = 30
GROUP_ID_DEFAULT = "F25PROJECTEC4D8"

# Primary prototype archive content.
PROTOTYPE_ITEMS = [
    "app.py",
    "smartcourse",
    "scripts",
    "templates",
    "static",
    "tests",
    "data",
    "models",
    "instance",
    "requirements.txt",
    "README.md",
    "start_project.ps1",
    "start_project.cmd",
    "start_project.sh",
]

# Fallback pack content for >30MB VULMS constraint (code folder only).
CODE_ONLY_ITEMS = [
    "app.py",
    "smartcourse",
    "scripts",
    "templates",
    "static",
    "tests",
    "requirements.txt",
    "README.md",
    "start_project.ps1",
    "start_project.cmd",
    "start_project.sh",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Automate prototype packaging according to submission instructions. "
            "Creates primary and fallback archives as needed."
        )
    )
    parser.add_argument(
        "--group-id",
        default=GROUP_ID_DEFAULT,
        help="Group ID used in generated ZIP names.",
    )
    parser.add_argument(
        "--output-dir",
        default="dist",
        help="Output directory where ZIP(s) and staging files are written.",
    )
    parser.add_argument(
        "--max-size-mb",
        type=float,
        default=MAX_MB_DEFAULT,
        help="VULMS ZIP size threshold in MB (default: 30).",
    )
    parser.add_argument(
        "--project-link",
        default="PASTE_GOOGLE_DRIVE_SHAREABLE_LINK_HERE",
        help="Google Drive link used in PROJECT_LINK.txt for >30MB fallback package.",
    )
    parser.add_argument(
        "--skip-sql-dump",
        action="store_true",
        help="Skip generating instance/smartcourse_dump.sql from SQLite database.",
    )
    parser.add_argument(
        "--clean-output",
        action="store_true",
        help="Delete output directory before packaging.",
    )
    return parser.parse_args()


def size_mb(path: Path) -> float:
    return round(path.stat().st_size / (1024 * 1024), 2)


def assert_required_paths(project_root: Path) -> None:
    required = [
        project_root / "app.py",
        project_root / "requirements.txt",
        project_root / "smartcourse",
        project_root / "scripts",
        project_root / "templates",
        project_root / "static",
    ]
    missing = [str(path.relative_to(project_root)) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required project paths: {', '.join(missing)}")


def make_sql_dump(project_root: Path, skip: bool) -> None:
    if skip:
        print("Skipping SQL dump generation (--skip-sql-dump).")
        return

    db_path = project_root / "instance" / "smartcourse.db"
    dump_path = project_root / "instance" / "smartcourse_dump.sql"
    if not db_path.exists():
        print("Database not found at instance/smartcourse.db. Skipping SQL dump generation.")
        return

    cmd = [
        sys.executable,
        "scripts/export_sql_dump.py",
        "--db",
        str(db_path),
        "--out",
        str(dump_path),
    ]
    print(f"Generating SQL dump: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(project_root), check=True)


def iter_files(base_path: Path):
    if base_path.is_file():
        yield base_path
        return
    for path in base_path.rglob("*"):
        if path.is_file():
            yield path


def zip_paths(project_root: Path, zip_path: Path, items: list[str], archive_root: str) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for rel in items:
            source = project_root / rel
            if not source.exists():
                print(f"Skipping missing path: {rel}")
                continue
            for file_path in iter_files(source):
                rel_file = file_path.relative_to(project_root)
                zf.write(file_path, arcname=f"{archive_root}/{rel_file.as_posix()}")


def copy_items(project_root: Path, items: list[str], destination_root: Path) -> None:
    destination_root.mkdir(parents=True, exist_ok=True)
    for rel in items:
        source = project_root / rel
        if not source.exists():
            print(f"Skipping missing path: {rel}")
            continue
        target = destination_root / rel
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def create_fallback_pack(
    project_root: Path,
    output_dir: Path,
    group_id: str,
    project_link: str,
) -> Path:
    stage_root = output_dir / f"SmartCourse_Prototype_Pack_{group_id}"
    if stage_root.exists():
        shutil.rmtree(stage_root)

    code_dir = stage_root / "code"
    db_dir = stage_root / "database"
    copy_items(project_root, CODE_ONLY_ITEMS, code_dir)

    db_dir.mkdir(parents=True, exist_ok=True)
    db_candidates = [
        project_root / "instance" / "smartcourse.db",
        project_root / "instance" / "smartcourse_dump.sql",
    ]
    for db_file in db_candidates:
        if db_file.exists():
            shutil.copy2(db_file, db_dir / db_file.name)

    (stage_root / "PROJECT_LINK.txt").write_text(
        project_link.strip() + "\n",
        encoding="utf-8",
    )

    zip_path = output_dir / f"SmartCourse_Prototype_Pack_{group_id}.zip"
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", root_dir=stage_root.parent, base_dir=stage_root.name)
    return zip_path


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parent.parent
    output_dir = (project_root / args.output_dir).resolve()

    if args.clean_output and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    assert_required_paths(project_root)
    make_sql_dump(project_root, skip=args.skip_sql_dump)

    archive_root = project_root.name
    prototype_zip = output_dir / f"SmartCourse_Prototype_{args.group_id}.zip"
    if prototype_zip.exists():
        prototype_zip.unlink()

    zip_paths(project_root, prototype_zip, PROTOTYPE_ITEMS, archive_root=archive_root)
    prototype_size_mb = size_mb(prototype_zip)

    print("\nPrototype ZIP created:")
    print(f"- Path: {prototype_zip}")
    print(f"- Size: {prototype_size_mb} MB")

    if prototype_size_mb <= args.max_size_mb:
        print(f"- Status: within {args.max_size_mb} MB limit, ready for VULMS upload.")
        return

    print(f"- Status: exceeds {args.max_size_mb} MB limit. Creating fallback submission pack.")
    fallback_zip = create_fallback_pack(
        project_root=project_root,
        output_dir=output_dir,
        group_id=args.group_id,
        project_link=args.project_link,
    )
    fallback_size = size_mb(fallback_zip)

    print("\nFallback ZIP created:")
    print(f"- Path: {fallback_zip}")
    print(f"- Size: {fallback_size} MB")
    print("- Contents: code/, database/, PROJECT_LINK.txt")
    if "PASTE_GOOGLE_DRIVE_SHAREABLE_LINK_HERE" in args.project_link:
        print("- Action needed: update PROJECT_LINK.txt with your actual Google Drive shareable link.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"Command failed with exit code {exc.returncode}: {exc.cmd}")
        raise SystemExit(exc.returncode)
    except Exception as exc:
        print(f"Packaging failed: {exc}")
        raise SystemExit(1)
