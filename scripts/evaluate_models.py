from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from typing import Iterable

from smartcourse.config import ProductionConfig
from smartcourse.models.neural_model import NeuralRecommender
from smartcourse.models.tfidf_model import TFIDFRecommender


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate recommenders on predefined queries.")
    parser.add_argument("--model-dir", dest="model_dir", help="Directory containing trained model artifacts.")
    parser.add_argument("--eval-file", dest="eval_file", help="JSON file with evaluation queries.")
    parser.add_argument("--k", dest="k", type=int, default=10, help="Cutoff for precision@k and recall@k.")
    return parser.parse_args()


def load_queries(path: str) -> list[dict[str, list[str]]]:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Evaluation file '{path}' not found. Create a JSON file with entries: "
            "{\"query\": str, \"relevant_titles\": [str, ...]}"
        )
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data


def precision_at_k(recommended: Iterable[str], relevant: set[str], k: int) -> float:
    top_items = list(recommended)[:k]
    if not top_items:
        return 0.0
    hits = sum(1 for item in top_items if item in relevant)
    return hits / min(k, len(top_items))


def recall_at_k(recommended: Iterable[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top_items = list(recommended)[:k]
    hits = sum(1 for item in top_items if item in relevant)
    return hits / len(relevant)


def hit_rate(recommended: Iterable[str], relevant: set[str], k: int) -> float:
    top_items = list(recommended)[:k]
    return 1.0 if any(item in relevant for item in top_items) else 0.0


def evaluate_model(model_name: str, model, queries: list[dict[str, list[str]]], k: int) -> dict[str, float]:
    scores = defaultdict(list)
    for entry in queries:
        query = entry["query"]
        relevant = {title.lower() for title in entry.get("relevant_titles", [])}
        results = model.recommend(query, top_n=k)
        titles = [item.get("course_title", "").lower() for item in results]
        scores["precision"].append(precision_at_k(titles, relevant, k))
        scores["recall"].append(recall_at_k(titles, relevant, k))
        scores["hit_rate"].append(hit_rate(titles, relevant, k))

    return {metric: sum(values) / len(values) if values else 0.0 for metric, values in scores.items()}


def main() -> None:
    args = parse_args()
    config = ProductionConfig()

    model_dir = args.model_dir or config.MODEL_CACHE_DIR
    eval_file = args.eval_file or os.path.join(os.path.dirname(config.DATASET_RAW_PATH), "evaluation_queries.json")
    k = args.k

    tfidf_path = os.path.join(model_dir, "tfidf_recommender.joblib")
    neural_path = os.path.join(model_dir, "neural_recommender.joblib")

    queries = load_queries(eval_file)

    tfidf_model = TFIDFRecommender.load(tfidf_path)
    neural_model = NeuralRecommender.load(neural_path)

    tfidf_scores = evaluate_model("TF-IDF", tfidf_model, queries, k)
    neural_scores = evaluate_model("Neural", neural_model, queries, k)

    print(f"Evaluation @ k={k}")
    print("Model\tPrecision\tRecall\tHit-Rate")
    print(
        f"TF-IDF\t{tfidf_scores['precision']:.3f}\t{tfidf_scores['recall']:.3f}\t{tfidf_scores['hit_rate']:.3f}"
    )
    print(
        f"Neural\t{neural_scores['precision']:.3f}\t{neural_scores['recall']:.3f}\t{neural_scores['hit_rate']:.3f}"
    )


if __name__ == "__main__":
    main()
