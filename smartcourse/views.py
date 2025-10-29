from __future__ import annotations

from flask import Blueprint, render_template

ui_bp = Blueprint("ui", __name__)


@ui_bp.route("/")
def home() -> str:
    return render_template("home.html")


@ui_bp.route("/recommend")
def recommend_page() -> str:
    return render_template("recommend.html")


@ui_bp.route("/dashboard")
def dashboard_page() -> str:
    return render_template("dashboard.html")


@ui_bp.route("/about")
def about_page() -> str:
    return render_template("about.html")
