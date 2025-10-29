from __future__ import annotations

from typing import Any

from sqlalchemy.orm.exc import NoResultFound

from ..extensions import db
from ..models import SavedRecommendation, SearchSession


class HistoryService:
    def create_session(
        self,
        preference: str,
        tfidf_results: list[dict[str, Any]] | None,
        neural_results: list[dict[str, Any]] | None,
    ) -> SearchSession:
        session = SearchSession(
            query_text=preference,
            tfidf_results=tfidf_results,
            neural_results=neural_results,
        )
        db.session.add(session)
        db.session.commit()
        return session

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        sessions = (
            SearchSession.query.order_by(SearchSession.created_at.desc()).limit(limit).all()
        )
        return [session.to_dict() for session in sessions]

    def save_recommendation(self, session_id: int, payload: dict[str, Any]) -> SavedRecommendation:
        session = SearchSession.query.get(session_id)
        if not session:
            raise NoResultFound(f"Search session {session_id} not found")

        recommendation = SavedRecommendation(
            session=session,
            model_type=payload.get("model_type", "unknown"),
            course_id=payload.get("course_id"),
            course_title=payload.get("course_title", "Untitled Course"),
            department=payload.get("department"),
            course_payload=payload,
            relevance_score=payload.get("score"),
        )
        db.session.add(recommendation)
        db.session.commit()
        return recommendation

    def get_saved(self, limit: int = 100) -> list[dict[str, Any]]:
        records = (
            SavedRecommendation.query.order_by(SavedRecommendation.saved_at.desc()).limit(limit).all()
        )
        return [record.to_dict() for record in records]

    def clear_all(self) -> int:
        """Remove all search sessions (and cascade saved recommendations)."""
        deleted = SearchSession.query.delete()
        db.session.commit()
        return deleted
