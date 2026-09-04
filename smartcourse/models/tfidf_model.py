from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..data.preprocess import normalize_text
from ..utils.model_artifacts import load_joblib


@dataclass(slots=True)
class TFIDFConfig:
    spacy_model: str = "en_core_web_sm"
    text_column: str = "processed_description"
    ngram_range: tuple[int, int] = (1, 2)
    # Keep this field in the serialized config for compatibility with model
    # artifacts created before the value was made configurable.
    min_df: int = 1
    max_df: float = 1.0


class TFIDFRecommender:
    def __init__(self, config: TFIDFConfig | None = None):
        self.config = config or TFIDFConfig()
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix: Any = None
        self.records: list[dict[str, Any]] = []

    def fit(self, frame: pd.DataFrame) -> "TFIDFRecommender":
        texts = _text_series(frame, self.config.text_column)
        self.vectorizer = TfidfVectorizer(
            ngram_range=self.config.ngram_range,
            min_df=self.config.min_df,
            max_df=self.config.max_df,
        )
        self.matrix = self.vectorizer.fit_transform(texts.tolist())
        self.records = _records(frame)
        return self

    def recommend(self, query: str, top_n: int = 10) -> list[dict[str, Any]]:
        if self.vectorizer is None or self.matrix is None:
            raise RuntimeError("TF-IDF recommender has not been fitted.")

        normalized_query = normalize_text(query, model_name=self.config.spacy_model) or query
        query_vector = self.vectorizer.transform([normalized_query])
        scores = cosine_similarity(query_vector, self.matrix).ravel()
        indices = np.argsort(-scores, kind="stable")[: max(0, int(top_n))]

        results: list[dict[str, Any]] = []
        for index in indices:
            item = dict(self.records[int(index)])
            item["score"] = float(scores[int(index)])
            item["model_type"] = "tfidf"
            results.append(item)
        return results

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: str) -> "TFIDFRecommender":
        artifact = load_joblib(path)

        # Current artifacts contain the recommender instance. Older builds
        # stored its components in a dictionary, so migrate that format when
        # loading instead of forcing every checkout to retrain the models.
        if isinstance(artifact, cls):
            artifact.config = _coerce_config(artifact.config)
            if not artifact.records and isinstance(getattr(artifact, "dataset", None), pd.DataFrame):
                artifact.records = _records(artifact.dataset)
            return artifact

        if isinstance(artifact, dict):
            dataset = artifact.get("dataset")
            if not isinstance(dataset, pd.DataFrame):
                raise TypeError("Legacy TF-IDF artifact is missing its dataset.")
            model = cls(_coerce_config(artifact.get("config")))
            model.vectorizer = artifact.get("vectorizer")
            model.matrix = artifact.get("matrix")
            model.records = _records(dataset)
            if model.vectorizer is None or model.matrix is None:
                raise TypeError("Legacy TF-IDF artifact is missing its vectorizer or matrix.")
            return model

        raise TypeError(f"Expected {cls.__name__} artifact, got {type(artifact).__name__}")


def _coerce_config(config: Any) -> TFIDFConfig:
    """Return a complete config even when loading older slotted dataclasses."""
    return TFIDFConfig(
        spacy_model=getattr(config, "spacy_model", "en_core_web_sm"),
        text_column=getattr(config, "text_column", "processed_description"),
        ngram_range=getattr(config, "ngram_range", (1, 2)),
        min_df=int(getattr(config, "min_df", 1)),
        max_df=float(getattr(config, "max_df", 1.0)),
    )


def _text_series(frame: pd.DataFrame, preferred_column: str) -> pd.Series:
    if preferred_column in frame.columns:
        return frame[preferred_column].fillna("").astype(str)
    if "recommendation_text" in frame.columns:
        return frame["recommendation_text"].fillna("").astype(str)
    return frame.apply(lambda row: " | ".join(str(value) for value in row.tolist()), axis=1)


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    records = frame.to_dict(orient="records")
    for index, record in enumerate(records):
        record.setdefault("course_id", str(index))
    return records
