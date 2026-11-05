"""Qdrant client wrapper"""
from typing import Optional, List
from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from core.config import settings
from core.exceptions import VectorStoreException
from core.logging import get_logger

logger = get_logger(__name__)


class QdrantClientWrapper:
    """Wrapper for Qdrant client operations"""
    
    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None):
        self.url = url or settings.QDRANT_URL
        self.api_key = api_key or settings.QDRANT_API_KEY
        self._client = None
        self._embeddings = None
    
    @property
    def client(self) -> QdrantClient:
        """Get or create Qdrant client"""
        if self._client is None:
            try:
                self._client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key
                )
                logger.info(f"Connected to Qdrant at {self.url}")
            except Exception as e:
                logger.error(f"Failed to connect to Qdrant: {str(e)}")
                raise VectorStoreException(
                    message="Failed to connect to Qdrant",
                    details={"error": str(e)}
                )
        return self._client
    
    @property
    def embeddings(self) -> OpenAIEmbeddings:
        """Get or create embeddings"""
        if self._embeddings is None:
            logger.info(f"Creating embeddings with API key: {settings.OPENAI_API_KEY}")
            self._embeddings = OpenAIEmbeddings(
                openai_api_key=settings.OPENAI_API_KEY
            )
        return self._embeddings
    
    def get_vector_store(self, collection_name: str) -> QdrantVectorStore:
        """Get vector store for collection"""
        try:
            vector_store = QdrantVectorStore(
                client=self.client,
                collection_name=collection_name,
                embedding=self.embeddings
            )
            logger.info(f"Created vector store for collection: {collection_name}")
            return vector_store
        except Exception as e:
            logger.error(f"Failed to create vector store: {str(e)}")
            raise VectorStoreException(
                message=f"Failed to create vector store for {collection_name}",
                details={"error": str(e)}
            )
    
    def get_retriever(self, collection_name: str, top_k: int = 200):
        """Get retriever for collection"""
        vector_store = self.get_vector_store(collection_name)
        return vector_store.as_retriever(search_kwargs={"k": top_k})
    
    def search(self, collection_name: str, query: str, top_k: int = 5) -> List[dict]:
        """Search in vector store"""
        try:
            retriever = self.get_retriever(collection_name, top_k=top_k)
            results = retriever.invoke(query)
            return results
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise VectorStoreException(
                message=f"Search failed in {collection_name}",
                details={"error": str(e), "query": query}
            )

