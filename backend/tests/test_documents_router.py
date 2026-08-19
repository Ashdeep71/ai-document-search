from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import documents as documents_router


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(
        documents_router, "UPLOAD_DIRECTORY", tmp_path / "uploads"
    )
    monkeypatch.setattr(
        documents_router, "PROCESSED_DIRECTORY", tmp_path / "processed"
    )
    monkeypatch.setattr(
        documents_router,
        "VECTORSTORES_DIRECTORY",
        tmp_path / "vectorstores",
    )

    documents_router.UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    documents_router.PROCESSED_DIRECTORY.mkdir(parents=True, exist_ok=True)
    documents_router.VECTORSTORES_DIRECTORY.mkdir(
        parents=True, exist_ok=True
    )

    return TestClient(app)


def upload_pdf(client, content=b"%PDF-1.4 fake pdf bytes"):
    return client.post(
        "/documents/upload",
        files={"file": ("document.pdf", content, "application/pdf")},
    )


def test_upload_rejects_non_pdf_content_type(client):
    response = client.post(
        "/documents/upload",
        files={"file": ("document.pdf", b"not a pdf", "text/plain")},
    )

    assert response.status_code == 400
    assert "Only PDF files" in response.json()["detail"]


def test_upload_rejects_non_pdf_extension(client):
    response = client.post(
        "/documents/upload",
        files={"file": ("document.txt", b"hello", "application/pdf")},
    )

    assert response.status_code == 400


def test_upload_rejects_empty_file(client):
    response = upload_pdf(client, content=b"")

    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_upload_rejects_file_larger_than_max_size(client, monkeypatch):
    monkeypatch.setattr(documents_router, "MAX_FILE_SIZE", 10)

    response = upload_pdf(client, content=b"x" * 100)

    assert response.status_code == 413


def test_upload_success_returns_document_id_and_processing_result(
    client, monkeypatch
):
    monkeypatch.setattr(
        documents_router,
        "process_pdf",
        lambda **kwargs: {
            "page_count": 2,
            "chunk_count": 5,
            "processed_filename": "doc.json",
            "embedding_model": "fake-embedding-model",
            "vector_count": 5,
            "vectorstore_directory": "fake-directory",
        },
    )

    response = upload_pdf(client)

    assert response.status_code == 201

    data = response.json()

    assert data["original_filename"] == "document.pdf"
    assert data["page_count"] == 2
    assert data["chunk_count"] == 5
    assert data["embedding_model"] == "fake-embedding-model"

    # Confirm the document_id is a real UUID string.
    assert uuid4().hex and len(data["document_id"]) == 36


def test_upload_cleans_up_file_when_processing_fails(client, monkeypatch):
    monkeypatch.setattr(
        documents_router,
        "process_pdf",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("bad pdf")),
    )

    response = upload_pdf(client)

    assert response.status_code == 422
    assert response.json()["detail"] == "bad pdf"
    assert list(documents_router.UPLOAD_DIRECTORY.iterdir()) == []


def test_search_document_returns_results(client, monkeypatch):
    monkeypatch.setattr(
        documents_router,
        "search_vector_store",
        lambda **kwargs: [
            {
                "page_content": "relevant text",
                "metadata": {"page_number": 3},
                "distance": 0.12,
            }
        ],
    )

    response = client.post(
        f"/documents/{uuid4()}/search",
        json={"query": "What is this about?", "k": 4},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["result_count"] == 1
    assert data["results"][0]["metadata"]["page_number"] == 3


def test_search_document_returns_404_when_index_missing(client, monkeypatch):
    def raise_not_found(**kwargs):
        raise FileNotFoundError("The vector store for this document was not found.")

    monkeypatch.setattr(
        documents_router, "search_vector_store", raise_not_found
    )

    response = client.post(
        f"/documents/{uuid4()}/search",
        json={"query": "What is this about?"},
    )

    assert response.status_code == 404


def test_ask_document_returns_document_id_key(client, monkeypatch):
    """Regression test: the /ask response previously returned a
    misspelled 'doucment_id' key instead of 'document_id'."""

    monkeypatch.setattr(
        documents_router,
        "answer_document_question",
        lambda **kwargs: {
            "answer": "This document is about testing.",
            "sources": [],
            "model": "fake-model",
            "retrieval_query": "What is this about?",
        },
    )

    document_id = str(uuid4())

    response = client.post(
        f"/documents/{document_id}/ask",
        json={"question": "What is this about?"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["document_id"] == document_id
    assert "doucment_id" not in data
    assert data["answer"] == "This document is about testing."


def test_ask_document_returns_404_when_index_missing(client, monkeypatch):
    def raise_not_found(**kwargs):
        raise FileNotFoundError("The vector store for this document was not found.")

    monkeypatch.setattr(
        documents_router, "answer_document_question", raise_not_found
    )

    response = client.post(
        f"/documents/{uuid4()}/ask",
        json={"question": "What is this about?"},
    )

    assert response.status_code == 404


def test_ask_document_returns_502_when_generation_fails(client, monkeypatch):
    def raise_generic_error(**kwargs):
        raise RuntimeError("The chat model returned an empty answer.")

    monkeypatch.setattr(
        documents_router, "answer_document_question", raise_generic_error
    )

    response = client.post(
        f"/documents/{uuid4()}/ask",
        json={"question": "What is this about?"},
    )

    assert response.status_code == 502
