# SmartCourse – AI Powered Course Recommendation System

SmartCourse is a dual-model recommendation platform that surfaces personalized university courses from a corpus of 8,500+ descriptions. A classical TF-IDF pipeline captures explicit keyword intent while a neural sentence-transformer model interprets semantic intent, letting learners compare both perspectives side-by-side.

## Features
- **Professional multi-page UI** built with Bootstrap 5 covering Home, Recommendations, Dashboard, and About pages.
- **Flask REST API** with `/api/recommend`, `/api/history`, and `/api/save` endpoints handled by a persistent SQLite store.
- **Dual recommendation engines**: TF-IDF + cosine similarity and semantic embeddings via `all-MiniLM-L6-v2`.
- **Data engineering toolkit** for cleaning, preprocessing (spaCy lemmatization), model training, and evaluation (precision@k, recall@k, hit-rate).
- **User analytics** including search histories, saved courses, model comparison panels, and one-click history/saved clearing.

## Project layout
```
smartcourse-ai-app/
├── app.py                  # Flask entrypoint
├── smartcourse/            # Application package
│   ├── api.py              # REST API blueprint
│   ├── config.py           # Configuration dataclasses
│   ├── data/               # Dataset preparation pipeline
│   ├── extensions.py       # SQLAlchemy & CORS instances
│   ├── models/             # DB models + recommendation engines
│   ├── services/           # Recommendation + history services
│   └── views.py            # UI routes
├── scripts/                # CLI utilities for dataset/model workflows
├── templates/              # Jinja templates for pages
├── static/                 # Bootstrap customisations & JS logic
└── tests/                  # (placeholder) automated tests
```

## Prerequisites
- Python 3.10+
- Virtual environment (recommended)
- Git LFS or direct download for the **Course Recommendation System dataset** (>=8,500 courses)
- Internet access to download spaCy & sentence-transformer models on first run

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## Step-by-step setup & launch
The commands below assume WSL or Linux/macOS. On Windows PowerShell, replace `source .venv/bin/activate` with `.venv\Scripts\activate`.

1. **Create an isolated environment**  
   Keeps project dependencies separate from the system interpreter.
   ```bash
   python3.10 -m venv .venv && source .venv/bin/activate
   ```

2. **Upgrade `pip` inside the venv**  
   Ensures we can pull the newest wheels.
   ```bash
   python -m pip install --upgrade pip
   ```

3. **Install CPU-only PyTorch**  
   Sentence-Transformers depends on PyTorch; the CPU wheel is lighter and works everywhere.
   ```bash
   pip install torch==2.5.1+cpu --index-url https://download.pytorch.org/whl/cpu
   ```

4. **Install project requirements**  
   Brings in Flask, scikit-learn, pandas, etc.
   ```bash
   pip install -r requirements.txt
   ```

5. **Download the spaCy language model**  
   Needed for lemmatization during preprocessing.
   ```bash
   python -m spacy download en_core_web_sm
   ```

6. **Add the Kaggle dataset**  
   Place `courses_dataset.csv` (provided) in the `data/` directory. If you download a different file, update `SMARTCOURSE_DATASET` or pass `--raw` to the scripts.

7. **Clean and preprocess the dataset**  
   Generates `data/courses_clean.csv` with normalized text ready for modeling.
   ```bash
   PYTHONPATH=. python scripts/prepare_data.py \
     --raw data/courses_dataset.csv \
     --processed data/courses_clean.csv \
     --min-length 10
   ```

8. **Train both recommenders**  
   Creates the TF-IDF and neural embedding artifacts in `models/`.
   ```bash
   PYTHONPATH=. python scripts/build_models.py \
     --data data/courses_clean.csv \
     --output models \
     --spacy-model en_core_web_sm \
     --embedding-model sentence-transformers/all-MiniLM-L6-v2
   ```

9. **(Optional) Evaluate the models**  
   Uses `data/evaluation_queries.json` to report precision/recall/hit-rate.
   ```bash
   PYTHONPATH=. python scripts/evaluate_models.py \
     --model-dir models \
     --eval-file data/evaluation_queries.json \
     --k 5
   ```

10. **Run the Flask app**  
    Serves the UI and REST API at `http://127.0.0.1:5000/`.
    ```bash
    SMARTCOURSE_MODEL_DIR=models \
    SMARTCOURSE_MAX_RESULTS=10 \
    PYTHONPATH=. python app.py --port 5000
    ```
    The first request will build `instance/smartcourse.db` automatically.

## Evaluation workflow
Provide labelled evaluation queries in `data/evaluation_queries.json`:
```json
[
  {
    "query": "Introductory Python for data science",
    "relevant_titles": ["Python for Data Science", "Applied Data Analysis"]
  }
]
```
Run quantitative comparison:
```bash
python scripts/evaluate_models.py --k 10
```
Displays precision@k, recall@k, and hit-rate for TF-IDF versus neural models.

## API reference
- `POST /api/recommend` – payload `{ "preference": str, "model": "tfidf"|"neural"|"hybrid", "top_n": optional }`
- `GET /api/history` – returns recent searches plus saved recommendations
- `POST /api/save` – persist a course: `{ "session_id": int, "course": {...} }`

All endpoints respond with JSON. Errors use HTTP status codes with descriptive messages.

## Configuration
Environment variables (optional):
- `SMARTCOURSE_DATASET` – raw dataset CSV path
- `SMARTCOURSE_DATASET_PROCESSED` – processed CSV path
- `SMARTCOURSE_MODEL_DIR` – directory for trained artifacts (default `models/`)
- `SMARTCOURSE_MAX_RESULTS` – number of recommendations to return (default 10)
- `SMARTCOURSE_EMBEDDING_MODEL` – SentenceTransformer name (default `sentence-transformers/all-MiniLM-L6-v2`)

## Next steps
- Integrate authentication for personalized dashboards per user
- Add background tasks to re-train embeddings as new datasets arrive
- Expand evaluation harness with qualitative review dashboards and automated regression checks

## License
Project materials are provided for educational use within the SmartCourse assignment scope.
