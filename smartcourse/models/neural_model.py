from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import joblib
import numpy as np
import pandas as pd

from ..utils.model_artifacts import load_joblib


@dataclass(slots=True)
class NeuralConfig:
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    text_column: str = "recommendation_text"
    batch_size: int = 32
    normalize_embeddings: bool = True
    # Keep this field in the serialized config for compatibility with model
    # artifacts created before progress reporting was hard-coded.
    show_progress_bar: bool = True


class NeuralRecommender:
    """Sentence-transformer recommender with a lazy, CPU-compatible encoder."""

    def __init__(self, config: NeuralConfig | None = None):
        self.config = config or NeuralConfig()
        self.embeddings: np.ndarray | None = None
        self.records: list[dict[str, Any]] = []
        self._encoder: Any = None

    def fit(self, frame: pd.DataFrame) -> "NeuralRecommender":
        texts = _text_series(frame, self.config.text_column).tolist()
        encoder = self._get_encoder()
        self.embeddings = np.asarray(
            encoder.encode(
                texts,
                batch_size=self.config.batch_size,
                show_progress_bar=self.config.show_progress_bar,
                convert_to_numpy=True,
                normalize_embeddings=self.config.normalize_embeddings,
            ),
            dtype=np.float32,
        )
        self.records = _records(frame)
        # Keep the artifact compact; the encoder is loaded lazily from the HF cache.
        self._encoder = None
        return self

    def recommend(self, query: str, top_n: int = 10) -> list[dict[str, Any]]:
        if self.embeddings is None:
            raise RuntimeError("Neural recommender has not been fitted.")

        query_embedding = np.asarray(
            self._get_encoder().encode(
                [query],
                convert_to_numpy=True,
                normalize_embeddings=self.config.normalize_embeddings,
            )[0],
            dtype=np.float32,
        )
        if self.config.normalize_embeddings:
            scores = self.embeddings @ query_embedding
        else:
            denominator = np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
            scores = (self.embeddings @ query_embedding) / np.maximum(denominator, 1e-12)

        indices = np.argsort(-scores, kind="stable")[: max(0, int(top_n))]
        results: list[dict[str, Any]] = []
        for index in indices:
            item = dict(self.records[int(index)])
            item["score"] = float(scores[int(index)])
            item["model_type"] = "neural"
            results.append(item)
        return results

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        encoder = self._encoder
        self._encoder = None
        try:
            joblib.dump(self, path)
        finally:
            self._encoder = encoder

    @classmethod
    def load(cls, path: str) -> "NeuralRecommender":
        artifact = load_joblib(path)

        # Current artifacts contain the recommender instance. Older builds
        # stored its components in a dictionary; migrate that format here so
        # existing model files remain usable on Windows and WSL.
        if isinstance(artifact, cls):
            artifact.config = _coerce_config(artifact.config)
            if not artifact.records and isinstance(getattr(artifact, "dataset", None), pd.DataFrame):
                artifact.records = _records(artifact.dataset)
            return artifact

        if isinstance(artifact, dict):
            dataset = artifact.get("dataset")
            if not isinstance(dataset, pd.DataFrame):
                raise TypeError("Legacy neural artifact is missing its dataset.")
            model = cls(_coerce_config(artifact.get("config")))
            model.embeddings = artifact.get("embeddings")
            model.records = _records(dataset)
            if model.embeddings is None:
                raise TypeError("Legacy neural artifact is missing its embeddings.")
            return model

        raise TypeError(f"Expected {cls.__name__} artifact, got {type(artifact).__name__}")

    def _get_encoder(self) -> Any:
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer

            self._encoder = SentenceTransformer(self.config.model_name, device="cpu")
        return self._encoder


def _coerce_config(config: Any) -> NeuralConfig:
    """Return a complete config even when loading older slotted dataclasses."""
    return NeuralConfig(
        model_name=getattr(config, "model_name", "sentence-transformers/all-MiniLM-L6-v2"),
        text_column=getattr(config, "text_column", "recommendation_text"),
        batch_size=int(getattr(config, "batch_size", 32)),
        normalize_embeddings=bool(
            getattr(config, "normalize_embeddings", True)
        ),
        show_progress_bar=bool(getattr(config, "show_progress_bar", True)),
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
