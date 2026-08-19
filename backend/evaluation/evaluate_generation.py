import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_openai import ChatOpenAI

from app.services.rag_service import answer_document_question, get_chat_model

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]

DEFAULT_EVAL_FILE = BACKEND_DIRECTORY / "evaluation" / "eval_questions.json"
RESULTS_DIRECTORY = BACKEND_DIRECTORY / "evaluation" / "results"

FAITHFULNESS_INSTRUCTIONS = """
You are grading whether an AI-generated answer is fully supported by the
provided source context.

Respond with exactly one word on the first line: YES if every factual claim
in the answer is supported by the context, or NO if the answer includes any
claim that is not supported by the context.

On the second line, give a one-sentence reason.
""".strip()

RELEVANCE_INSTRUCTIONS = """
You are grading whether an AI-generated answer actually addresses the
user's question, regardless of whether the answer is factually correct.

Respond with exactly one word on the first line: YES if the answer directly
addresses the question, or NO if it does not.

On the second line, give a one-sentence reason.
""".strip()


def parse_verdict(response_text: str) -> str:
    """Extract a yes/no/unknown verdict from a judge model's first line."""

    stripped = response_text.strip()

    if not stripped:
        return "unknown"

    first_line = stripped.splitlines()[0].strip().upper()

    if first_line.startswith("YES"):
        return "yes"

    if first_line.startswith("NO"):
        return "no"

    return "unknown"


def run_judge(
    model: ChatOpenAI,
    instructions: str,
    user_content: str,
) -> dict[str, str]:
    messages = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": user_content},
    ]

    response = model.invoke(messages)
    response_text = response.text.strip()

    return {
        "verdict": parse_verdict(response_text),
        "raw_response": response_text,
    }


def judge_faithfulness(
    model: ChatOpenAI,
    question: str,
    answer: str,
    context: str,
) -> dict[str, str]:
    user_content = (
        f"Question:\n{question}\n\n"
        f"Answer:\n{answer}\n\n"
        f"Source context:\n{context}"
    )

    return run_judge(model, FAITHFULNESS_INSTRUCTIONS, user_content)


def judge_relevance(
    model: ChatOpenAI,
    question: str,
    answer: str,
) -> dict[str, str]:
    user_content = f"Question:\n{question}\n\nAnswer:\n{answer}"

    return run_judge(model, RELEVANCE_INSTRUCTIONS, user_content)


def evaluate_generation(
    eval_file: Path,
    k: int,
    limit: int | None = None,
) -> dict[str, Any]:
    eval_data = json.loads(eval_file.read_text(encoding="utf-8"))

    document_id = eval_data["document_id"]
    cases = eval_data["cases"]

    if limit is not None:
        cases = cases[:limit]

    index_directory = (
        BACKEND_DIRECTORY / "data" / "vectorstores" / document_id
    )

    judge_model, model_name = get_chat_model()

    case_results = []

    for case in cases:
        question = case["question"]

        rag_result = answer_document_question(
            index_directory=index_directory,
            question=question,
            history=[],
            k=k,
        )

        answer = rag_result["answer"]
        sources = rag_result["sources"]

        if not sources:
            case_results.append(
                {
                    "question": question,
                    "answer": answer,
                    "abstained": True,
                    "faithfulness": None,
                    "relevance": None,
                }
            )
            continue

        context = rag_result["context"]

        faithfulness = judge_faithfulness(
            judge_model, question, answer, context
        )
        relevance = judge_relevance(judge_model, question, answer)

        case_results.append(
            {
                "question": question,
                "answer": answer,
                "abstained": False,
                "faithfulness": faithfulness,
                "relevance": relevance,
            }
        )

    judged_cases = [
        case_result
        for case_result in case_results
        if not case_result["abstained"]
    ]

    judged_count = len(judged_cases)

    faithful_count = sum(
        1
        for case_result in judged_cases
        if case_result["faithfulness"]["verdict"] == "yes"
    )
    relevant_count = sum(
        1
        for case_result in judged_cases
        if case_result["relevance"]["verdict"] == "yes"
    )

    summary = {
        "question_count": len(case_results),
        "abstained_count": len(case_results) - judged_count,
        "judged_count": judged_count,
        "faithfulness_rate": (
            faithful_count / judged_count if judged_count else None
        ),
        "relevance_rate": (
            relevant_count / judged_count if judged_count else None
        ),
    }

    return {
        "document_id": document_id,
        "model": model_name,
        "k": k,
        "cases": case_results,
        "summary": summary,
    }


def print_results(results: dict[str, Any]) -> None:
    for case_result in results["cases"]:
        print("\nQuestion:", case_result["question"])
        print("Answer:", case_result["answer"])

        if case_result["abstained"]:
            print("Abstained: the model reported no supporting context.")
            continue

        print(
            "Faithfulness:",
            case_result["faithfulness"]["verdict"],
            "-",
            case_result["faithfulness"]["raw_response"].splitlines()[-1],
        )
        print(
            "Relevance:",
            case_result["relevance"]["verdict"],
            "-",
            case_result["relevance"]["raw_response"].splitlines()[-1],
        )

    summary = results["summary"]

    print("\n-----------------------")
    print(f"Document: {results['document_id']}")
    print(f"Judge model: {results['model']}")
    print(f"Questions: {summary['question_count']}")
    print(f"Abstained: {summary['abstained_count']}")

    if summary["judged_count"]:
        print(f"Faithfulness rate: {summary['faithfulness_rate']:.2%}")
        print(f"Relevance rate: {summary['relevance_rate']:.2%}")
    else:
        print("No answers were judged (all questions were abstained).")


def save_results(results: dict[str, Any]) -> Path:
    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    output_path = (
        RESULTS_DIRECTORY
        / f"generation_{results['document_id']}_{timestamp}.json"
    )

    output_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate generation quality (faithfulness and relevance) "
            "using an LLM judge. Makes real LLM calls for both the "
            "answer and the judge, so cost scales with question count."
        ),
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
        default=4,
        help="Number of chunks to retrieve for each answer.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only evaluate the first N questions (useful for a cheap smoke test).",
    )

    args = parser.parse_args()

    results = evaluate_generation(
        eval_file=args.eval_file,
        k=args.k,
        limit=args.limit,
    )

    print_results(results)

    output_path = save_results(results)
    print(f"\nResults written to {output_path}")


if __name__ == "__main__":
    main()
