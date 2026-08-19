from pathlib import Path
from uuid import UUID, uuid4
from app.services.document_processor import process_pdf
from pydantic import BaseModel, Field
from typing import Literal

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.services.vector_store import search_vector_store

import logging

from app.services.rag_service import answer_document_question

logger= logging.getLogger(__name__)

class DocumentSearchRequest(BaseModel):
    query: str = Field(
       min_length=1,
       max_length= 500,
    )
    k: int= Field(
       default=4, 
       ge=1,
       le=10
    )

class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(
        min_length=1,
        max_length=4000,
    )

class DocumentQuestionRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=1000,
    )

    k: int = Field(
        default=4,
        ge=1,
        le=8,
    )

    history: list[ChatHistoryMessage] = Field(
        default_factory=list,
        max_length=10,
    )





router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

BACKEND_DIRECTORY = Path(__file__).resolve().parents[2]

UPLOAD_DIRECTORY = BACKEND_DIRECTORY / "data" / "uploads"



UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)


PROCESSED_DIRECTORY = BACKEND_DIRECTORY / "data" / "processed"
PROCESSED_DIRECTORY.mkdir(parents=True, exist_ok=True)

VECTORSTORES_DIRECTORY = (
    BACKEND_DIRECTORY / "data" / "vectorstores"
)

VECTORSTORES_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
READ_CHUNK_SIZE = 1024 * 1024  # 1 MB


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
       file: UploadFile,
       ) -> dict[str,str | int]:
      """Validate and save one PDF document."""
      original_filename = file.filename or ""
        # Basic PDF validation.
      if (
        file.content_type != "application/pdf"
        or not original_filename.lower().endswith(".pdf")
    ):
        await file.close()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported.",
        )

      document_id = str(uuid4())
      stored_filename = f"{document_id}.pdf"
      destination = UPLOAD_DIRECTORY / stored_filename

      total_size = 0


      try:
        with destination.open("wb") as output_file:
            while chunk := await file.read(READ_CHUNK_SIZE):
                total_size += len(chunk)

                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="The PDF must be 10 MB or smaller.",
                    )

                output_file.write(chunk)

        if total_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded PDF is empty.",
            )

      except HTTPException:
        # Remove an empty or partially saved file.
        destination.unlink(missing_ok=True)
        raise

      except OSError as error:
        destination.unlink(missing_ok=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The server could not save the PDF.",
        ) from error

      finally:
         await file.close()

      try:
          processing_result = process_pdf(
          pdf_path=destination,
          processed_directory=PROCESSED_DIRECTORY,
          vectorstores_directory= VECTORSTORES_DIRECTORY,
          document_id=document_id,
          original_filename=original_filename,
    )
      except ValueError as error:
        destination.unlink(missing_ok=True)

        raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(error),
         ) from error


      return {
         "document_id": document_id,
         "original_filename": original_filename,
          "stored_filename": stored_filename,
          "size_bytes": total_size,
           "message": "PDF uploaded and processed successfully.",
          **processing_result,
}



@router.post("/{document_id}/search")
def search_document(
    document_id:UUID,
    request: DocumentSearchRequest,

)-> dict :
     """
    Retrieve chunks that are semantically related to a question.

    This performs retrieval only. It does not generate an AI answer yet.
    """
     document_id_string = str(document_id)

     index_directory = (
        VECTORSTORES_DIRECTORY / document_id_string
    )

     try:
        results= search_vector_store(
           index_directory= index_directory,
           query= request.query,
           k= request.k,
        )

     except FileNotFoundError as error:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail= str(error),
        ) from error

     except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

     return {
        "document_id": document_id_string,
        "query": request.query,
        "result_count": len(results),
        "results": results,
     }


@router.post("/{document_id}/ask")
def ask_document(
    document_id:UUID,
    request: DocumentQuestionRequest,
)-> dict: 

 """
    Retrieve relevant PDF chunks and generate a grounded answer.
    """

 document_id_string= str(document_id)
 index_directory= (
    VECTORSTORES_DIRECTORY / document_id_string
 )

 try: 
    history = [
    {
        "role": message.role,
        "content": message.content,
    }
    for message in request.history
]
    rag_result= answer_document_question(
       index_directory= index_directory,
       question= request.question,
       history=history,
       k= request.k,
    )


 except FileNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error


 except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


 except Exception as error:
        logger.exception(
            "Answer generation failed for document %s",
            document_id_string,
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "The document was searched, but the AI answer "
                "could not be generated."
            ),
        ) from error


 return {
     "document_id": document_id_string,
     "question": request.question,
     **rag_result,
 }







 


 
