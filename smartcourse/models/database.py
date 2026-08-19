from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..extensions import db


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SearchSession(db.Model):
    __tablename__ = "search_sessions"

    id = db.Column(db.Integer, primary_key=True)
    query_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_utc_now)
    tfidf_results = db.Column(db.JSON, nullable=True)
    neural_results = db.Column(db.JSON, nullable=True)

    saved_recommendations = db.relationship(
        "SavedRecommendation",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "query_text": self.query_text,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "tfidf_results": self.tfidf_results or [],
            "neural_results": self.neural_results or [],
            "saved_recommendations": [record.to_dict() for record in self.saved_recommendations],
        }


class SavedRecommendation(db.Model):
    __tablename__ = "saved_recommendations"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("search_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_type = db.Column(db.String(32), nullable=False, default="unknown")
    course_id = db.Column(db.String(255), nullable=True)
    course_title = db.Column(db.String(500), nullable=False, default="Untitled Course")
    department = db.Column(db.String(255), nullable=True)
    course_payload = db.Column(db.JSON, nullable=False, default=dict)
    relevance_score = db.Column(db.Float, nullable=True)
    saved_at = db.Column(db.DateTime, nullable=False, default=_utc_now)

    session = db.relationship("SearchSession", back_populates="saved_recommendations")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "model_type": self.model_type,
            "course_id": self.course_id,
            "course_title": self.course_title,
            "department": self.department,
            "metadata": self.course_payload or {},
            "relevance_score": self.relevance_score,
            "saved_at": self.saved_at.isoformat() if self.saved_at else None,
        }
