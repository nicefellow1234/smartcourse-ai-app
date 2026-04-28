from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Mapping, Sequence

import pandas as pd

from .preprocess import WHITESPACE_RE, preprocess_series

CANONICAL_COLUMN_ALIASES: Mapping[str, Sequence[str]] = {
    "course_title": ("Course Name", "Title", "Course Title"),
    "university": ("University", "School", "Created by", "Site"),
    "difficulty": ("Difficulty Level", "Level"),
    "rating": ("Course Rating", "Rating", "Number of ratings"),
    "course_description": ("Course Description", "Short Intro", "Course Short Intro", "What you learn"),
    "department": ("Department", "Sub-Category", "Category", "COURSE CATEGORIES"),
}


@dataclass(slots=True)
class PipelineConfig:
    raw_path: str
    processed_path: str
    spacy_model: str = "en_core_web_sm"
    min_description_length: int = 40


class CourseDataPipeline:
    def __init__(self, config: PipelineConfig):
        self.config = config

    def load_raw(self) -> pd.DataFrame:
        if not os.path.exists(self.config.raw_path):
            raise FileNotFoundError(
                f"Dataset not found at '{self.config.raw_path}'. Update SMARTCOURSE_DATASET or place the file accordingly."
            )
        df = pd.read_csv(self.config.raw_path)
        df = self._ensure_required_columns(df)
        return df

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.drop_duplicates(subset=["course_title", "course_description"], keep="first")
        df = df.dropna(subset=["course_description"])
        df = df[df["course_description"].str.len() >= self.config.min_description_length]
        df = df.drop(columns=[col for col in df.columns if str(col).lower().startswith("unnamed:")], errors="ignore")
        df["department"] = df["department"].fillna("General Studies")
        if "Category" in df.columns:
            df["department"] = df["department"].where(df["department"].notna() & (df["department"].str.strip() != ""), df["Category"])
        df["difficulty"] = df["difficulty"].fillna("Not Specified")
        df["university"] = self._coalesce_text_columns(df, ["university", "Site", "Created by"]).fillna(
            "Independent Provider"
        )
        df["rating"] = df["rating"].map(self._coerce_rating).fillna(0)
        df["course_title"] = df["course_title"].fillna("Untitled Course").str.strip()
        df["course_description"] = df["course_description"].fillna("").str.strip()
        df["recommendation_text"] = self._build_recommendation_text(df)
        return df.reset_index(drop=True)

    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        processed = df.copy()
        processed["processed_description"] = preprocess_series(
            processed["recommendation_text"], model_name=self.config.spacy_model
        )
        return processed

    def save(self, df: pd.DataFrame) -> None:
        os.makedirs(os.path.dirname(self.config.processed_path), exist_ok=True)
        df.to_csv(self.config.processed_path, index=False)

    def run(self, save: bool = True) -> pd.DataFrame:
        df = self.load_raw()
        df = self.clean(df)
        df = self.preprocess(df)
        if save:
            self.save(df)
        return df

    def _ensure_required_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        rename_map: dict[str, str] = {}
        for canonical, aliases in CANONICAL_COLUMN_ALIASES.items():
            for alias in aliases:
                if alias in df.columns:
                    rename_map[alias] = canonical
                    break
            else:
                human_aliases = ", ".join(aliases)
                raise ValueError(
                    f"Dataset missing a column for '{canonical}'. Expected one of: {human_aliases}."
                )

        df = df.rename(columns=rename_map)

        # Build richer descriptions when possible by cascading alternative text fields.
        if "course_description" in df.columns:
            description = df["course_description"].fillna("")
            for fallback_column in ("What you learn", "Course Short Intro", "Short Intro"):
                if fallback_column in df.columns:
                    fallback_values = df[fallback_column].fillna("")
                    description = description.where(description.str.strip() != "", fallback_values)
            df["course_description"] = description

        return df

    @staticmethod
    def _coerce_rating(value) -> float | None:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value)
        match = re.search(r"(\d+(?:\.\d+)?)", text)
        if not match:
            return None
        try:
            return float(match.group(1))
        except ValueError:
            return None

    @staticmethod
    def _coalesce_text_columns(df: pd.DataFrame, columns: Sequence[str]) -> pd.Series:
        result = pd.Series([None] * len(df), index=df.index, dtype="object")
        for column in columns:
            if column not in df.columns:
                continue
            values = df[column].fillna("").astype(str).str.strip()
            result = result.where(result.fillna("").astype(str).str.strip() != "", values)
        return result.replace("", pd.NA)

    @staticmethod
    def _build_recommendation_text(df: pd.DataFrame) -> pd.Series:
        text_columns = [
            "course_title",
            "course_description",
            "Course Short Intro",
            "What you learn",
            "Skills",
            "Category",
            "department",
            "COURSE CATEGORIES",
            "Course Type",
            "difficulty",
            "university",
            "Instructors",
            "Prequisites",
            "Program",
        ]
        available = [column for column in text_columns if column in df.columns]

        def join_row(row: pd.Series) -> str:
            parts: list[str] = []
            seen: set[str] = set()
            for column in available:
                value = row.get(column)
                if value is None or (isinstance(value, float) and pd.isna(value)):
                    continue
                text = str(value).strip()
                if not text or text.lower() == "nan":
                    continue
                normalized = WHITESPACE_RE.sub(" ", text).lower()
                if normalized in seen:
                    continue
                seen.add(normalized)
                parts.append(text)
            return " | ".join(parts)

        return df.apply(join_row, axis=1)
