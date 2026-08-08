import json
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from app.services.vector_store import create_vector_store



CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# rag ipileline proccesses the pdf file and splits it into chunks and saves it as json file in the processed directory. The json file containers the chunks and their metadata.
# The metadata contains the document id, filename, page number, chunk index and chunk id. The chunk id is a combination of the document id and the page index.


def extract_pdf_pages(
    pdf_path: Path,
    document_id: str,
    original_filename: str,
) -> list[Document]:
    """
    Extract readable text from each PDF page.

    Each readable page becomes one LangChain Document with metadata
    describing where the text came from.
    """

    try:
        reader = PdfReader(str(pdf_path))
    except (PdfReadError, OSError) as error:
        raise ValueError("The uploaded PDF could not be read.") from error

    if reader.is_encrypted:
        raise ValueError(
            "Password-protected PDFs are not supported yet."
        )

    pages: list[Document] = []

    for page_number, page in enumerate(reader.pages, start=1):
        extracted_text = page.extract_text() or ""
        cleaned_text = extracted_text.strip()

        # Some PDF pages may contain no extractable text.
        if not cleaned_text:
            continue

        page_document = Document(
            page_content=cleaned_text,
            metadata={
                "document_id": document_id,
                "filename": original_filename,
                "page_number": page_number,
            },
        )

        pages.append(page_document)

    if not pages:
        raise ValueError(
            "No readable text was found in the PDF."
        )

    return pages


def split_pages_into_chunks(
    pages: list[Document],
) -> list[Document]:
    """
    Split page documents into smaller overlapping chunks.

    LangChain preserves each page's metadata when creating chunks.
    """

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = text_splitter.split_documents(pages)

    for chunk_index, chunk in enumerate(chunks):
        document_id = chunk.metadata["document_id"]

        chunk.metadata["chunk_index"] = chunk_index
        chunk.metadata["chunk_id"] = (
            f"{document_id}-chunk-{chunk_index}"
        )

    return chunks


def save_chunks_as_json(
    chunks: list[Document],
    output_path: Path,
) -> None:
    """Save chunks temporarily so we can inspect the results."""

    serializable_chunks = []

    for chunk in chunks:
        serializable_chunks.append(
            {
                "page_content": chunk.page_content,
                "metadata": chunk.metadata,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(
            serializable_chunks,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def process_pdf(
    pdf_path: Path,
    processed_directory: Path,
    vectorstores_directory: Path,
    document_id: str,
    original_filename: str,
) -> dict[str, str | int]:
    """
    Run the complete non-AI document-processing workflow.

    1. Extract pages
    2. Split pages into chunks
    3. Save chunks as JSON
    """

    pages = extract_pdf_pages(
        pdf_path=pdf_path,
        document_id=document_id,
        original_filename=original_filename,
    )

    chunks = split_pages_into_chunks(pages)

    output_path = processed_directory / f"{document_id}.json"

    save_chunks_as_json(
        chunks=chunks,
        output_path=output_path,
    )

    vectorstore_path = (
        vectorstores_directory / document_id
    )
    vector_result= create_vector_store(chunks= chunks,
                        index_directory= vectorstore_path)

    return {
        "page_count": len(pages),
        "chunk_count": len(chunks),
        "processed_filename": output_path.name,
        **vector_result,
    }