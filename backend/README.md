# AI Document Search — Backend

FastAPI backend for the AI Document Search RAG application. See the [root README](../README.md) for the full project overview, architecture, and setup instructions.

## Development

```bash
uv sync
uv run uvicorn app.main:app --reload
```

The API is served at `http://127.0.0.1:8000`, with interactive docs at `/docs`.

## Tests

```bash
uv run pytest
```

## Retrieval evaluation

`evaluation/evaluate_retrieval.py` measures recall@k, precision@k, and MRR@k for a document against a labeled question set (`evaluation/eval_questions.json`):

```bash
uv run python -m evaluation.evaluate_retrieval --k 1 3 5
```

Results are written to `evaluation/results/` (git-ignored) for comparing runs after chunking, embedding, or prompt changes.
