import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.vector_store import search_vector_store

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]

DEFAULT_EVAL_FILE = BACKEND_DIRECTORY / "evaluation" / "eval_questions.json"
RESULTS_DIRECTORY = BACKEND_DIRECTORY / "evaluation" / "results"


def is_hit(expected_pages: set[int], retrieved_pages: list[int]) -> bool:
    """Whether any expected page appears among the retrieved pages."""

    return bool(expected_pages & set(retrieved_pages))


def precision_at_k(expected_pages: set[int], retrieved_pages: list[int]) -> float:
    """Fraction of retrieved pages that are expected pages."""

    if not retrieved_pages:
        return 0.0

    relevant_count = sum(
        1 for page in retrieved_pages if page in expected_pages
    )

    return relevant_count / len(retrieved_pages)


def reciprocal_rank(expected_pages: set[int], retrieved_pages: list[int]) -> float:
    """1 / rank of the first retrieved page that is an expected page, else 0."""

    for rank, page in enumerate(retrieved_pages, start=1):
        if page in expected_pages:
            return 1 / rank

    return 0.0


def evaluate_retrieval(
    eval_file: Path,
    k_values: list[int],
) -> dict[str, Any]:
    eval_data = json.loads(eval_file.read_text(encoding="utf-8"))

    document_id = eval_data["document_id"]
    cases = eval_data["cases"]

    index_directory = (
        BACKEND_DIRECTORY / "data" / "vectorstores" / document_id
    )

    max_k = max(k_values)

    case_results = []

    for case in cases:
        question = case["question"]
        expected_pages = set(case["expected_pages"])

        matches = search_vector_store(
            index_directory=index_directory,
            query=question,
            k=max_k,
        )

        retrieved_pages = [
            match["metadata"]["page_number"] for match in matches
        ]

        case_results.append(
            {
                "question": question,
                "expected_pages": sorted(expected_pages),
                "retrieved_pages": retrieved_pages,
            }
        )

    summary_by_k = {}

    for k in k_values:
        recall_hits = []
        precision_scores = []
        reciprocal_ranks = []

        for case_result in case_results:
            expected_pages = set(case_result["expected_pages"])
            top_k_pages = case_result["retrieved_pages"][:k]

            recall_hits.append(is_hit(expected_pages, top_k_pages))
            precision_scores.append(
                precision_at_k(expected_pages, top_k_pages)
            )
            reciprocal_ranks.append(
                reciprocal_rank(expected_pages, top_k_pages)
            )

        total = len(case_results)

        summary_by_k[str(k)] = {
            "recall": sum(recall_hits) / total if total else 0.0,
            "precision": sum(precision_scores) / total if total else 0.0,
            "mrr": sum(reciprocal_ranks) / total if total else 0.0,
        }

    return {
        "document_id": document_id,
        "eval_file": str(eval_file),
        "question_count": len(case_results),
        "k_values": k_values,
        "cases": case_results,
        "summary_by_k": summary_by_k,
    }


def print_results(results: dict[str, Any]) -> None:
    for case_result in results["cases"]:
        print("\nQuestion:", case_result["question"])
        print("Expected pages:", case_result["expected_pages"])
        print("Retrieved pages:", case_result["retrieved_pages"])

    print("\n-----------------------")
    print(f"Document: {results['document_id']}")
    print(f"Questions: {results['question_count']}")

    for k in results["k_values"]:
        summary = results["summary_by_k"][str(k)]

        print(
            f"k={k}: "
            f"recall={summary['recall']:.2%} "
            f"precision={summary['precision']:.2%} "
            f"mrr={summary['mrr']:.3f}"
        )


def save_results(results: dict[str, Any]) -> Path:
    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    output_path = (
        RESULTS_DIRECTORY / f"{results['document_id']}_{timestamp}.json"
    )

    output_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate retrieval quality against a labeled question set.",
    )

    parser.add_argument(
        "--eval-file",
        type=Path,
        default=DEFAULT_EVAL_FILE,
        help="Path to a JSON file with 'document_id' and 'cases'.",
    )

    parser.add_argument(
        "--k",
        type=int,
        nargs="+",
        default=[4],
        help="One or more k values to evaluate, e.g. --k 1 3 5",
    )

    args = parser.parse_args()

    results = evaluate_retrieval(
        eval_file=args.eval_file,
        k_values=args.k,
    )

    print_results(results)

    output_path = save_results(results)
    print(f"\nResults written to {output_path}")


if __name__ == "__main__":
    main()
