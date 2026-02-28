# SmartCourse - AI Powered Course Recommendation System

SmartCourse is a Flask web app that recommends courses from an 8,500+ course catalog using two ranking approaches:
- TF-IDF (keyword-focused)
- Neural sentence embeddings (semantic-focused)

## Prototype Metadata
- Group ID: `F25PROJECTEC4D8`
- Roll No: `BC240419615`
- Supervisor: Muhammad Bilal (`bilal.saleem@vu.edu.pk`)
- Note: If your group has 2 members, add both names/roll numbers here before final submission.

## Prototype Compliance Checklist (Fall 2025_CS619_11727_3.docx)
- Multi-page Bootstrap UI: `Home`, `Recommendations`, `Dashboard`, `About`
- Recommendation page with natural language input, model selection, top results, score bars, and save action
- Dashboard with search history, saved recommendations, and side-by-side TF-IDF vs Neural comparison
- Flask API implemented:
  - `POST /api/recommend`
  - `GET /api/history`
  - `POST /api/save`
- SQLite persistence for sessions and saved recommendations
- Data cleaning, model training, and evaluation scripts in `scripts/`
- Operational logging enabled in `instance/smartcourse.log`

## Project Structure
```text
smartcourse-ai-app/
|-- app.py
|-- smartcourse/
|   |-- api.py
|   |-- views.py
|   |-- services/
|   |-- models/
|   `-- data/
|-- scripts/
|-- templates/
|-- static/
|-- data/
|-- models/
|-- instance/
`-- project-documents/
```

## 1) Setup (Windows PowerShell)
Run from the project root:

```powershell
python -m venv .venv-win
.\.venv-win\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## One-Command Startup (Recommended)
This script auto-detects Windows/Linux/WSL and then:
- creates the correct virtual environment if missing
- checks prerequisites (Python version, required files, pip, packages, spaCy model)
- installs missing dependencies
- prepares data/models if artifacts are missing
- starts the Flask app

PowerShell:
```powershell
.\start_project.ps1
```

Command Prompt (`cmd`):
```bat
start_project.cmd
```

Linux/WSL:
```bash
./start_project.sh
```

If Python is not installed, the wrapper shows install instructions first.  
`start_project.ps1` also supports optional auto-install:
```powershell
.\start_project.ps1 -InstallPython
```

Optional app args:
PowerShell:
```powershell
.\start_project.ps1 --host 127.0.0.1 --port 5000 --debug
```
Command Prompt (`cmd`):
```bat
start_project.cmd --host 127.0.0.1 --port 5000 --debug
```
Linux/WSL:
```bash
./start_project.sh --host 127.0.0.1 --port 5000 --debug
```

Force rebuild/reprepare options:
PowerShell:
```powershell
.\start_project.ps1 --force-build-models
.\start_project.ps1 --force-prepare-data
.\start_project.ps1 --force-prepare-data --force-build-models
```
Command Prompt (`cmd`):
```bat
start_project.cmd --force-build-models
start_project.cmd --force-prepare-data
start_project.cmd --force-prepare-data --force-build-models
```
Linux/WSL:
```bash
./start_project.sh --force-build-models
./start_project.sh --force-prepare-data
./start_project.sh --force-prepare-data --force-build-models
```

Use this when you see model compatibility warnings (for example, scikit-learn version mismatch while loading `.joblib` models).

## 2) Prepare Data (if needed)
```powershell
$env:PYTHONPATH='.'
python scripts\prepare_data.py --raw data\courses_dataset.csv --processed data\courses_clean.csv --min-length 10
```

## 3) Build Models (if needed)
```powershell
$env:PYTHONPATH='.'
python scripts\build_models.py --data data\courses_clean.csv --output models --spacy-model en_core_web_sm --embedding-model sentence-transformers/all-MiniLM-L6-v2
```

## 4) Run the App
Minimum command required by assignment brief:

```powershell
$env:PYTHONPATH='.'
python app.py
```

Optional custom host/port:

```powershell
$env:PYTHONPATH='.'
python app.py --host 127.0.0.1 --port 5000 --debug
```

Open: `http://127.0.0.1:5000`

## 5) Quick API Checks
```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/api/recommend -ContentType 'application/json' -Body '{"preference":"I want to learn Python for data science","model":"hybrid","top_n":10}'
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:5000/api/history
```

## 6) Logging and Database
- API events and recommendation traces are written to `instance/smartcourse.log`
- SQLite DB file: `instance/smartcourse.db`

Export a portable SQL dump:

```powershell
python scripts\export_sql_dump.py --db instance\smartcourse.db --out instance\smartcourse_dump.sql
```

## 7) Evaluation (Optional)
```powershell
$env:PYTHONPATH='.'
python scripts\evaluate_models.py --model-dir models --eval-file data\evaluation_queries.json --k 5
```

## 8) Submission Packaging (Prototype Phase)
From `Fall 2025_CS619_11727_3.docx`:
- If archive size is less than 30 MB:
  - Submit complete project folder as `.zip` on VULMS.
- If archive size is greater than 30 MB:
  - Put application code in one folder.
  - Put DB file(s) in another folder.
  - Add a text file containing a shareable Google Drive link of full project.

Automation script (excludes `project-documents/` by default):
```powershell
python scripts\package_prototype.py --group-id F25PROJECTEC4D8 --project-link "https://drive.google.com/your-share-link"
```

What it does:
- creates `dist/SmartCourse_Prototype_<GROUP_ID>.zip`
- excludes `project-documents/` from prototype ZIP
- auto-checks ZIP size against 30 MB
- if over limit, auto-creates `dist/SmartCourse_Prototype_Pack_<GROUP_ID>.zip` with:
  - `code/`
  - `database/`
  - `PROJECT_LINK.txt`
- auto-generates `instance/smartcourse_dump.sql` when DB exists

## Tech Stack
- Python 3.10+
- Flask, Flask-SQLAlchemy, Flask-Cors
- pandas, numpy, scikit-learn
- spaCy, sentence-transformers, joblib
- Bootstrap 5 + vanilla JavaScript (Fetch API)
