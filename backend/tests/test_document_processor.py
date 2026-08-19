import json
from pathlib import Path

import pytest
from langchain_core.documents import Document
from pypdf.errors import PdfReadError

from app.services import document_processor


class FakePage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class FakeReader:
    def __init__(self, pages, is_encrypted=False):
        self.pages = pages
        self.is_encrypted = is_encrypted


def test_extract_pdf_pages_skips_blank_pages_and_keeps_original_numbering(
    monkeypatch,
):
    fake_reader = FakeReader(
        pages=[
            FakePage("Hello world"),
            FakePage("   "),
            FakePage("Third page"),
        ]
    )

    monkeypatch.setattr(
        document_processor, "PdfReader", lambda path: fake_reader
    )

    pages = document_processor.extract_pdf_pages(
        pdf_path=Path("fake.pdf"),
        document_id="doc-1",
        original_filename="fake.pdf",
    )

    assert [page.page_content for page in pages] == [
        "Hello world",
        "Third page",
    ]
    assert [page.metadata["page_number"] for page in pages] == [1, 3]
    assert all(page.metadata["document_id"] == "doc-1" for page in pages)
    assert all(
        page.metadata["filename"] == "fake.pdf" for page in pages
    )


def test_extract_pdf_pages_rejects_encrypted_pdf(monkeypatch):
    fake_reader = FakeReader(pages=[FakePage("secret")], is_encrypted=True)

    monkeypatch.setattr(
        document_processor, "PdfReader", lambda path: fake_reader
    )

    with pytest.raises(ValueError, match="Password-protected"):
        document_processor.extract_pdf_pages(
            pdf_path=Path("fake.pdf"),
            document_id="doc-1",
            original_filename="fake.pdf",
        )


def test_extract_pdf_pages_rejects_unreadable_pdf(monkeypatch):
    def raise_read_error(path):
        raise PdfReadError("corrupt")

    monkeypatch.setattr(document_processor, "PdfReader", raise_read_error)

    with pytest.raises(ValueError, match="could not be read"):
        document_processor.extract_pdf_pages(
            pdf_path=Path("fake.pdf"),
            document_id="doc-1",
            original_filename="fake.pdf",
        )


def test_extract_pdf_pages_rejects_pdf_with_no_readable_text(monkeypatch):
    fake_reader = FakeReader(pages=[FakePage(""), FakePage("   ")])

    monkeypatch.setattr(
        document_processor, "PdfReader", lambda path: fake_reader
    )

    with pytest.raises(ValueError, match="No readable text"):
        document_processor.extract_pdf_pages(
            pdf_path=Path("fake.pdf"),
            document_id="doc-1",
            original_filename="fake.pdf",
        )


def test_split_pages_into_chunks_preserves_metadata_and_adds_chunk_fields():
    long_text = "Sentence one. " * 200

    pages = [
        Document(
            page_content=long_text,
            metadata={
                "document_id": "doc-1",
                "filename": "fake.pdf",
                "page_number": 1,
            },
        )
    ]

    chunks = document_processor.split_pages_into_chunks(pages)

    assert len(chunks) > 1

    for chunk_index, chunk in enumerate(chunks):
        assert chunk.metadata["document_id"] == "doc-1"
        assert chunk.metadata["filename"] == "fake.pdf"
        assert chunk.metadata["page_number"] == 1
        assert chunk.metadata["chunk_index"] == chunk_index
        assert chunk.metadata["chunk_id"] == f"doc-1-chunk-{chunk_index}"


def test_save_chunks_as_json_writes_readable_json(tmp_path):
    chunks = [
        Document(
            page_content="content one",
            metadata={"chunk_id": "doc-1-chunk-0"},
        ),
        Document(
            page_content="content two",
            metadata={"chunk_id": "doc-1-chunk-1"},
        ),
    ]

    output_path = tmp_path / "nested" / "doc-1.json"

    document_processor.save_chunks_as_json(chunks, output_path)

    saved = json.loads(output_path.read_text(encoding="utf-8"))

    assert saved == [
        {
            "page_content": "content one",
            "metadata": {"chunk_id": "doc-1-chunk-0"},
        },
        {
            "page_content": "content two",
            "metadata": {"chunk_id": "doc-1-chunk-1"},
        },
    ]


def test_process_pdf_orchestrates_pipeline_and_returns_combined_result(
    monkeypatch, tmp_path
):
    fake_pages = [
        Document(
            page_content="page text",
            metadata={
                "document_id": "doc-1",
                "filename": "fake.pdf",
                "page_number": 1,
            },
        )
    ]

    fake_chunks = [
        Document(
            page_content="page text",
            metadata={
                "document_id": "doc-1",
                "filename": "fake.pdf",
                "page_number": 1,
                "chunk_index": 0,
                "chunk_id": "doc-1-chunk-0",
            },
        )
    ]

    monkeypatch.setattr(
        document_processor,
        "extract_pdf_pages",
        lambda **kwargs: fake_pages,
    )
    monkeypatch.setattr(
        document_processor,
        "split_pages_into_chunks",
        lambda pages: fake_chunks,
    )
    monkeypatch.setattr(
        document_processor,
        "create_vector_store",
        lambda chunks, index_directory: {
            "embedding_model": "fake-embedding-model",
            "vector_count": len(chunks),
            "vectorstore_directory": str(index_directory),
        },
    )

    processed_directory = tmp_path / "processed"
    vectorstores_directory = tmp_path / "vectorstores"

    result = document_processor.process_pdf(
        pdf_path=tmp_path / "fake.pdf",
        processed_directory=processed_directory,
        vectorstores_directory=vectorstores_directory,
        document_id="doc-1",
        original_filename="fake.pdf",
    )

    assert result["page_count"] == 1
    assert result["chunk_count"] == 1
    assert result["processed_filename"] == "doc-1.json"
    assert result["embedding_model"] == "fake-embedding-model"
    assert result["vector_count"] == 1
    assert (processed_directory / "doc-1.json").exists()
