from __future__ import annotations

import argparse
from pathlib import Path

from smartcourse.config import ProductionConfig
from smartcourse.data import CourseDataPipeline, PipelineConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean and preprocess the course dataset.")
    parser.add_argument("--raw", dest="raw_path", help="Path to raw dataset CSV.")
    parser.add_argument("--processed", dest="processed_path", help="Target path for cleaned CSV.")
    parser.add_argument("--spacy-model", dest="spacy_model", default="en_core_web_sm", help="spaCy model name.")
    parser.add_argument("--min-length", dest="min_length", type=int, default=40, help="Minimum description length.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = ProductionConfig()

    raw_path = args.raw_path or config.DATASET_RAW_PATH
    processed_path = args.processed_path or config.DATASET_PROCESSED_PATH

    pipeline = CourseDataPipeline(
        PipelineConfig(
            raw_path=raw_path,
            processed_path=processed_path,
            spacy_model=args.spacy_model,
            min_description_length=args.min_length,
        )
    )

    df = pipeline.run(save=True)
    print(f"Processed {len(df):,} courses -> {processed_path}")
    print("Columns:", ", ".join(df.columns))


if __name__ == "__main__":
    main()
