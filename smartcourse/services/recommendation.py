from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any, Literal

from flask import current_app

from ..models import NeuralRecommender, TFIDFRecommender

ModelChoice = Literal["tfidf", "neural", "hybrid"]


@dataclass(slots=True)
class RecommendationResult:
    preference: str
    model: ModelChoice
    results: dict[str, list[dict[str, Any]]]


class RecommendationService:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self._tfidf_model: TFIDFRecommender | None = None
        self._neural_model: NeuralRecommender | None = None

    @property
    def tfidf_model(self) -> TFIDFRecommender:
        if self._tfidf_model is None:
            path = self._model_path("tfidf_recommender.joblib")
            if not os.path.exists(path):
                raise FileNotFoundError(
                    f"TF-IDF model artifact missing at '{path}'. Run scripts/build_models.py to train it."
                )
            self._tfidf_model = TFIDFRecommender.load(path)
        return self._tfidf_model

    @property
    def neural_model(self) -> NeuralRecommender:
        if self._neural_model is None:
            path = self._model_path("neural_recommender.joblib")
            if not os.path.exists(path):
                raise FileNotFoundError(
                    f"Neural model artifact missing at '{path}'. Run scripts/build_models.py to train it."
                )
            self._neural_model = NeuralRecommender.load(path)
        return self._neural_model

    def recommend(self, preference: str, model: ModelChoice, top_n: int | None = None) -> RecommendationResult:
        if not preference:
            raise ValueError("Preference text is required")
        top_n = top_n or int(self.config.get("MAX_RESULTS", 10))

        response: dict[str, list[dict[str, Any]]] = {}
        if model in ("tfidf", "hybrid"):
            tfidf_items = self._normalize_scores(self.tfidf_model.recommend(preference, top_n=top_n))
            response["tfidf"] = tfidf_items
            if model == "tfidf":
                response["items"] = tfidf_items
        if model in ("neural", "hybrid"):
            neural_items = self._normalize_scores(self.neural_model.recommend(preference, top_n=top_n))
            response["neural"] = neural_items
            if model == "neural":
                response["items"] = neural_items

        return RecommendationResult(preference=preference, model=model, results=response)

    def reload(self) -> None:
        self._tfidf_model = None
        self._neural_model = None

    def _model_path(self, filename: str) -> str:
        base_dir = self.config.get("MODEL_CACHE_DIR")
        return os.path.join(base_dir, filename)

    @staticmethod
    def _normalize_scores(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in items:
            score = float(item.get("score", 0))
            if item.get("model_type") == "neural":
                score = (score + 1.0) / 2.0  # cosine similarity [-1,1] -> [0,1]
            score = max(0.0, min(1.0, score))
            normalized_item = {
                "course_title": item.get("course_title"),
                "course_id": item.get("course_id"),
                "url": item.get("URL") or item.get("Course URL") or item.get("url"),
                "department": item.get("department"),
                "university": item.get("university"),
                "description": item.get("course_description"),
                "category": item.get("Category") or item.get("COURSE CATEGORIES"),
                "course_type": item.get("Course Type"),
                "difficulty": item.get("difficulty"),
                "rating": item.get("rating"),
                "reviews": item.get("Number of Reviews") or item.get("Number of ratings"),
                "viewers": item.get("Number of viewers"),
                "duration": item.get("Duration"),
                "language": item.get("Language"),
                "subtitle_languages": item.get("Subtitle Languages"),
                "skills": item.get("Skills"),
                "instructors": item.get("Instructors"),
                "what_you_learn": item.get("What you learn"),
                "prerequisites": item.get("Prequisites"),
                "program": item.get("Program") or item.get("Program Type"),
                "price": item.get("Price"),
                "weekly_study": item.get("Weekly study"),
                "premium_course": item.get("Premium course"),
                "included": item.get("What's include"),
                "score": score,
                "model_type": item.get("model_type"),
            }
            cleaned_item = {key: RecommendationService._clean_value(value) for key, value in normalized_item.items()}
            if cleaned_item["university"] is None:
                cleaned_item["university"] = "Independent Provider"
            if cleaned_item["department"] is None:
                cleaned_item["department"] = "General Studies"
            if cleaned_item["description"] is None:
                cleaned_item["description"] = ""
            normalized.append(cleaned_item)
        return normalized

    @staticmethod
    def _clean_value(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return None
            return float(value)
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        return value


def get_recommendation_service() -> RecommendationService:
    app = current_app
    service: RecommendationService | None = app.extensions.get("recommendation_service")
    if service is None:
        service = RecommendationService(app.config)
        app.extensions["recommendation_service"] = service
    return service
