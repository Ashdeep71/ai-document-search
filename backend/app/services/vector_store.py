import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

BACKEND_DIRECTORY = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIRECTORY / ".env"
load_dotenv(ENV_FILE)

EMBEDDING_MODEL = "text-embedding-3-small"

def get_embedding_model() -> OpenAIEmbeddings:

    """
    Create the embedding-model connection used for both:

    1. Embedding PDF chunks
    2. Embedding user questions
    """

    api_key= os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY was not found in the environment variables.")


    return OpenAIEmbeddings(model= EMBEDDING_MODEL, 
                        api_key= api_key,)



def create_vector_store(chunks: list[Document],
                        index_directory: Path,
)-> dict[str, str | int]:
      """
    Generate embeddings for the chunks and save them in FAISS.
    """
      if not chunks:
           raise ValueError(  "Cannot create a vector store without document chunks.")

      embedding_model = get_embedding_model()

      vector_store= FAISS.from_documents(documents= chunks, embedding= embedding_model,)

      index_directory.mkdir(parents=True, exist_ok=True)


      vector_store.save_local(str(index_directory))


      return {
           "embedding_model": EMBEDDING_MODEL,
           "vector_count": len(chunks),
           "vectorstore_directory": str(index_directory)
      }



def search_vector_store(index_directory: Path, query: str, k:int =4,)-> list[dict[str,any]]:
       """
    Find the PDF chunks most semantically related to a question.
    """

       if not query.strip():
            raise ValueError("Query cannot be empty or whitespace.")

       faiss_file= index_directory/"index.faiss"
       metadata_file= index_directory/"index.pkl"

       if not faiss_file.exists() or not metadata_file.exists():
         raise FileNotFoundError(
            "The vector store for this document was not found."
        )

       embedding_model= get_embedding_model()

       
       vector_store= FAISS.load_local(str(index_directory), embeddings= embedding_model,
         allow_dangerous_deserialization=True,)

       matches= vector_store.similarity_search_with_score(query= query,k=k)

       results: list[dict[str,any]]= []
       for document, distance in matches:
              results.append({
                   "page_content": document.page_content,
                    "metadata":document.metadata,
                    "distance": float(distance)              })


       return results


