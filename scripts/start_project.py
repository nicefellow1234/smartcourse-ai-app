from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

MIN_PYTHON = (3, 10)
PACKAGE_CHECKS = [
    ("flask", "Flask"),
    ("flask_sqlalchemy", "Flask-SQLAlchemy"),
    ("flask_cors", "Flask-Cors"),
    ("pandas", "pandas"),
    ("numpy", "numpy"),
    ("sklearn", "scikit-learn"),
    ("spacy", "spacy"),
    ("sentence_transformers", "sentence-transformers"),
    ("joblib", "joblib"),
    ("dotenv", "python-dotenv"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "SmartCourse bootstrap runner: detects environment, prepares virtualenv, "
            "installs dependencies, and starts the Flask app."
        )
    )
    parser.add_argument("--host", default="127.0.0.1", help="Flask host interface.")
    parser.add_argument("--port", type=int, default=5000, help="Flask port.")
    parser.add_argument("--venv-dir", help="Override virtualenv path.")
    parser.add_argument("--skip-install", action="store_true", help="Skip pip upgrade and requirements install.")
    parser.add_argument("--skip-spacy-download", action="store_true", help="Skip spaCy model check/download.")
    parser.add_argument("--skip-prepare-data", action="store_true", help="Skip data preparation if clean data is missing.")
    parser.add_argument("--skip-build-models", action="store_true", help="Skip model build if artifacts are missing.")
    parser.add_argument("--force-prepare-data", action="store_true", help="Run data preparation even if clean data exists.")
    parser.add_argument("--force-build-models", action="store_true", help="Run model build even if artifacts exist.")
    parser.add_argument("--max-results", type=int, default=10, help="SMARTCOURSE_MAX_RESULTS value.")
    parser.add_argument(
        "--embedding-model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Embedding model used by scripts/build_models.py.",
    )

    debug_group = parser.add_mutually_exclusive_group()
    debug_group.add_argument("--debug", action="store_true", help="Enable Flask debug mode.")
    debug_group.add_argument("--no-debug", action="store_true", help="Disable Flask debug mode.")

    return parser.parse_args()


def detect_environment() -> str:
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    if system == "linux":
        release = platform.release().lower()
        if "microsoft" in release:
            return "wsl"
        proc_version = Path("/proc/version")
        if proc_version.exists() and "microsoft" in proc_version.read_text(encoding="utf-8", errors="ignore").lower():
            return "wsl"
        return "linux"
    if system == "darwin":
        return "macos"
    return system


def default_venv_dir(project_root: Path, environment: str) -> Path:
    if environment == "windows":
        return project_root / ".venv-win"
    return project_root / ".venv"


def venv_python_path(venv_dir: Path, environment: str) -> Path:
    if environment == "windows":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"\n> {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd), env=env, check=True)


def run_capture(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def ensure_launcher_python_version() -> None:
    if sys.version_info[:2] < MIN_PYTHON:
        raise RuntimeError(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required. "
            f"Current: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )


def ensure_project_files(project_root: Path) -> None:
    required = [
        project_root / "requirements.txt",
        project_root / "app.py",
        project_root / "scripts" / "prepare_data.py",
        project_root / "scripts" / "build_models.py",
        project_root / "scripts" / "evaluate_models.py",
        project_root / "smartcourse" / "__init__.py",
    ]
    missing = [str(path.relative_to(project_root)) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required project file(s): {', '.join(missing)}")


def ensure_pip_available(project_root: Path, python_path: Path) -> None:
    try:
        run_capture([str(python_path), "-m", "pip", "--version"], cwd=project_root)
    except subprocess.CalledProcessError:
        run([str(python_path), "-m", "ensurepip", "--upgrade"], cwd=project_root)


def ensure_venv_python_version(project_root: Path, python_path: Path) -> None:
    version = run_capture(
        [
            str(python_path),
            "-c",
            "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')",
        ],
        cwd=project_root,
    )
    major_minor = tuple(int(part) for part in version.split(".", 1))
    if major_minor < MIN_PYTHON:
        raise RuntimeError(
            f"Virtualenv python must be {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ but is {version}. "
            "Create venv with a supported interpreter."
        )


def detect_missing_packages(project_root: Path, python_path: Path) -> list[str]:
    checks_literal = ", ".join(f"('{mod}', '{pkg}')" for mod, pkg in PACKAGE_CHECKS)
    script = (
        "import importlib.util\n"
        f"checks = [{checks_literal}]\n"
        "missing = [pkg for mod, pkg in checks if importlib.util.find_spec(mod) is None]\n"
        "print('\\n'.join(missing))\n"
    )
    output = run_capture([str(python_path), "-c", script], cwd=project_root)
    if not output:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def ensure_venv(project_root: Path, environment: str, args: argparse.Namespace) -> tuple[Path, Path]:
    venv_dir = Path(args.venv_dir).resolve() if args.venv_dir else default_venv_dir(project_root, environment)
    python_path = venv_python_path(venv_dir, environment)

    if python_path.exists():
        print(f"Using existing virtualenv: {venv_dir}")
        return venv_dir, python_path

    print(f"Creating virtualenv: {venv_dir}")
    run([sys.executable, "-m", "venv", str(venv_dir)], cwd=project_root)

    python_path = venv_python_path(venv_dir, environment)
    if not python_path.exists():
        raise FileNotFoundError(f"Virtualenv created but python executable not found at {python_path}")
    return venv_dir, python_path


def ensure_dependencies(project_root: Path, python_path: Path, args: argparse.Namespace) -> None:
    ensure_pip_available(project_root, python_path)
    missing = detect_missing_packages(project_root, python_path)

    if not missing:
        print("All required Python packages are already installed.")
        return

    print("Missing Python packages detected:")
    for package in missing:
        print(f"- {package}")

    if args.skip_install:
        raise RuntimeError("Missing packages detected but --skip-install was provided.")

    run([str(python_path), "-m", "pip", "install", "--upgrade", "pip"], cwd=project_root)
    run([str(python_path), "-m", "pip", "install", "-r", "requirements.txt"], cwd=project_root)

    missing_after_install = detect_missing_packages(project_root, python_path)
    if missing_after_install:
        raise RuntimeError(
            "Some required Python packages are still missing after installation: "
            + ", ".join(missing_after_install)
        )


def ensure_spacy_model(project_root: Path, python_path: Path, args: argparse.Namespace) -> None:
    if args.skip_spacy_download:
        print("Skipping spaCy model check/download (--skip-spacy-download).")
        return

    check_cmd = [
        str(python_path),
        "-c",
        "import spacy; spacy.load('en_core_web_sm'); print('spaCy model en_core_web_sm ready')",
    ]
    try:
        run(check_cmd, cwd=project_root)
    except subprocess.CalledProcessError:
        print("spaCy model 'en_core_web_sm' not found. Downloading now.")
        run([str(python_path), "-m", "spacy", "download", "en_core_web_sm"], cwd=project_root)


def ensure_prepared_data(project_root: Path, python_path: Path, args: argparse.Namespace) -> None:
    processed_path = project_root / "data" / "courses_clean.csv"
    if processed_path.exists() and not args.force_prepare_data:
        print(f"Using existing processed dataset: {processed_path}")
        return
    if args.skip_prepare_data and not args.force_prepare_data:
        print("Skipping data preparation (--skip-prepare-data).")
        return

    raw_candidates = [
        project_root / "data" / "courses_dataset.csv",
        project_root / "data" / "courses_raw.csv",
    ]
    raw_path = next((path for path in raw_candidates if path.exists()), None)
    if raw_path is None:
        raise FileNotFoundError(
            "No raw dataset found. Expected one of: data/courses_dataset.csv or data/courses_raw.csv"
        )

    run(
        [
            str(python_path),
            "scripts/prepare_data.py",
            "--raw",
            str(raw_path),
            "--processed",
            str(processed_path),
            "--min-length",
            "10",
        ],
        cwd=project_root,
        env=build_env(project_root, max_results=args.max_results),
    )


def ensure_models(project_root: Path, python_path: Path, args: argparse.Namespace) -> None:
    model_dir = project_root / "models"
    tfidf_path = model_dir / "tfidf_recommender.joblib"
    neural_path = model_dir / "neural_recommender.joblib"

    has_models = tfidf_path.exists() and neural_path.exists()
    if has_models and not args.force_build_models:
        print(f"Using existing model artifacts in: {model_dir}")
        return
    if args.skip_build_models and not args.force_build_models:
        print("Skipping model build (--skip-build-models).")
        return

    processed_path = project_root / "data" / "courses_clean.csv"
    if not processed_path.exists():
        raise FileNotFoundError(
            "Processed dataset missing at data/courses_clean.csv. "
            "Run without --skip-prepare-data or provide the file."
        )

    run(
        [
            str(python_path),
            "scripts/build_models.py",
            "--data",
            str(processed_path),
            "--output",
            str(model_dir),
            "--spacy-model",
            "en_core_web_sm",
            "--embedding-model",
            args.embedding_model,
        ],
        cwd=project_root,
        env=build_env(project_root, max_results=args.max_results),
    )


def build_env(project_root: Path, max_results: int) -> dict[str, str]:
    env = os.environ.copy()
    current_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(project_root)
        if not current_pythonpath
        else f"{project_root}{os.pathsep}{current_pythonpath}"
    )
    env.setdefault("SMARTCOURSE_MODEL_DIR", str(project_root / "models"))
    env["SMARTCOURSE_MAX_RESULTS"] = str(max_results)
    return env


def run_app(project_root: Path, python_path: Path, args: argparse.Namespace) -> None:
    app_cmd = [str(python_path), "app.py", "--host", args.host, "--port", str(args.port)]
    if args.debug:
        app_cmd.append("--debug")
    elif args.no_debug:
        app_cmd.append("--no-debug")

    env = build_env(project_root, max_results=args.max_results)

    print("\nSmartCourse startup summary:")
    print(f"- URL: http://{args.host}:{args.port}")
    print(f"- PYTHONPATH: {env['PYTHONPATH']}")
    print(f"- SMARTCOURSE_MODEL_DIR: {env['SMARTCOURSE_MODEL_DIR']}")
    print(f"- SMARTCOURSE_MAX_RESULTS: {env['SMARTCOURSE_MAX_RESULTS']}")
    print("- Log file: instance/smartcourse.log")

    run(app_cmd, cwd=project_root, env=env)


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parent.parent
    environment = detect_environment()
    ensure_launcher_python_version()
    ensure_project_files(project_root)

    print("Detected environment:")
    print(f"- OS: {platform.system()} {platform.release()}")
    print(f"- Mode: {environment}")
    print(f"- Project root: {project_root}")

    venv_dir, venv_python = ensure_venv(project_root, environment, args)
    print(f"- Virtualenv: {venv_dir}")
    print(f"- Python: {venv_python}")
    ensure_venv_python_version(project_root, venv_python)

    ensure_dependencies(project_root, venv_python, args)
    ensure_spacy_model(project_root, venv_python, args)
    ensure_prepared_data(project_root, venv_python, args)
    ensure_models(project_root, venv_python, args)
    run_app(project_root, venv_python, args)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"\nCommand failed with exit code {exc.returncode}: {exc.cmd}")
        raise SystemExit(exc.returncode)
    except Exception as exc:
        print(f"\nStartup failed: {exc}")
        raise SystemExit(1)
