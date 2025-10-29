from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.orm.exc import NoResultFound

from .services import HistoryService, get_recommendation_service

api_bp = Blueprint("api", __name__)
history_service = HistoryService()


@api_bp.post("/recommend")
def recommend():
    payload = request.get_json(silent=True) or {}

    preference = (payload.get("preference") or "").strip()
    model = (payload.get("model") or "hybrid").lower()
    top_n = payload.get("top_n")

    if model not in {"tfidf", "neural", "hybrid"}:
        return jsonify({"error": f"Unsupported model '{model}'. Use tfidf, neural, or hybrid."}), 400
    if not preference:
        return jsonify({"error": "Preference text is required."}), 400

    try:
        service = get_recommendation_service()
        recommendation = service.recommend(preference, model=model, top_n=top_n)
        session = history_service.create_session(
            preference=preference,
            tfidf_results=recommendation.results.get("tfidf"),
            neural_results=recommendation.results.get("neural"),
        )
        response = {
            "preference": recommendation.preference,
            "model": recommendation.model,
            "results": recommendation.results,
            "session_id": session.id,
            "created_at": session.created_at.isoformat() if session.created_at else None,
        }
        return jsonify(response)
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 503
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:  # pragma: no cover
        current_app.logger.exception("Failed to compute recommendations")
        return jsonify({"error": "Internal server error"}), 500


@api_bp.get("/history")
def history():
    history_records = history_service.get_history()
    saved = history_service.get_saved()
    return jsonify({"history": history_records, "saved": saved})


@api_bp.delete("/history")
def clear_history():
    deleted = history_service.clear_all()
    return jsonify({"cleared_sessions": deleted})


@api_bp.delete("/saved")
def clear_saved():
    deleted = history_service.clear_saved()
    return jsonify({"cleared_saved": deleted})


@api_bp.post("/save")
def save():
    payload = request.get_json(silent=True) or {}
    session_id = payload.get("session_id")
    course = payload.get("course") or {}

    if not session_id:
        return jsonify({"error": "session_id is required."}), 400
    if not isinstance(course, dict):
        return jsonify({"error": "course payload must be an object."}), 400

    try:
        record = history_service.save_recommendation(session_id=int(session_id), payload=course)
        return jsonify({"saved": record.to_dict()}), 201
    except NoResultFound as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception:  # pragma: no cover
        current_app.logger.exception("Failed to save recommendation")
        return jsonify({"error": "Internal server error"}), 500
