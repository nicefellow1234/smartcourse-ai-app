from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

from smartcourse.config import ProductionConfig
from smartcourse.models.neural_model import NeuralConfig, NeuralRecommender
from smartcourse.models.tfidf_model import TFIDFConfig, TFIDFRecommender


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train TF-IDF and neural embedding recommenders.")
    parser.add_argument("--data", dest="data_path", help="Path to preprocessed course CSV.")
    parser.add_argument("--output", dest="output_dir", help="Directory for model artifacts.")
    parser.add_argument("--spacy-model", dest="spacy_model", default="en_core_web_sm", help="spaCy model for query preprocessing.")
    parser.add_argument("--embedding-model", dest="embedding_model", help="SentenceTransformer model name.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = ProductionConfig()

    data_path = args.data_path or config.DATASET_PROCESSED_PATH
    output_dir = args.output_dir or config.MODEL_CACHE_DIR
    embedding_model = args.embedding_model or config.EMBEDDING_MODEL_NAME

    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Processed dataset missing at '{data_path}'. Run scripts/prepare_data.py first.")

    df = pd.read_csv(data_path)
    os.makedirs(output_dir, exist_ok=True)

    tfidf_model = TFIDFRecommender(TFIDFConfig(spacy_model=args.spacy_model))
    tfidf_model.fit(df)
    tfidf_path = os.path.join(output_dir, "tfidf_recommender.joblib")
    tfidf_model.save(tfidf_path)
    print(f"Saved TF-IDF model to {tfidf_path}")

    neural_model = NeuralRecommender(NeuralConfig(model_name=embedding_model, text_column="recommendation_text"))
    neural_model.fit(df)
    neural_path = os.path.join(output_dir, "neural_recommender.joblib")
    neural_model.save(neural_path)
    print(f"Saved neural model to {neural_path}")


if __name__ == "__main__":
    main()
