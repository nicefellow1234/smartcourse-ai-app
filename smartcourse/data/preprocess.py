from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable

import pandas as pd

try:
    import spacy
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("spaCy must be installed to preprocess text.") from exc


HTML_TAG_RE = re.compile(r"<[^>]+>")
NON_ALPHA_RE = re.compile(r"[^a-zA-Z\s]")
WHITESPACE_RE = re.compile(r"\s+")


@lru_cache(maxsize=2)
def get_spacy_model(model_name: str = "en_core_web_sm"):
    try:
        return spacy.load(model_name, disable=["ner", "parser"])
    except OSError as exc:  # pragma: no cover
        raise RuntimeError(
            f"spaCy model '{model_name}' is not installed. Run 'python -m spacy download {model_name}'."
        ) from exc


def normalize_text(text: str, model_name: str = "en_core_web_sm") -> str:
    if not isinstance(text, str):
        return ""

    lowered = text.lower()
    no_html = HTML_TAG_RE.sub(" ", lowered)
    clean = NON_ALPHA_RE.sub(" ", no_html)
    clean = WHITESPACE_RE.sub(" ", clean).strip()
    if not clean:
        return ""

    nlp = get_spacy_model(model_name)
    doc = nlp(clean)
    tokens = [token.lemma_ for token in doc if token.is_alpha and not token.is_stop]
    return " ".join(tokens)


def preprocess_series(series: pd.Series, model_name: str = "en_core_web_sm") -> pd.Series:
    return series.fillna("").apply(lambda x: normalize_text(x, model_name=model_name))


def batch_iter(series: Iterable[str], batch_size: int = 256) -> Iterable[list[str]]:
    batch: list[str] = []
    for item in series:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch
