"""
LangChain-based RAG Service

Phase 1-2: Core RAG implementation using LangChain LCEL.

This service provides a cleaner, more maintainable RAG pipeline compared to
the manual implementation, using LangChain's declarative chains.
"""

from uuid import UUID
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.core.langchain_config import get_langchain_llm, get_langchain_embeddings, RAG_PROMPT
from app.db.vector_store import VectorStoreManager
from app.modules.askai.db.repository import ChatRepository
from langchain_core.output_parsers import StrOutputParser


class LangChainRAGService:
    """
    RAG service using LangChain chains (Phase 1+).

    This is a stub implementation for Phase 1. Phase 2 will add full functionality.
    """

    def __init__(self, vector_store: VectorStoreManager, db: Session):
        """
        Initialize LangChain RAG service.

        Args:
            vector_store: VectorStoreManager instance for document retrieval
            db: SQLAlchemy database session
        """
        self.vector_store = vector_store
        self.db = db
        self.chat_repo = ChatRepository(db)

        # Lazily initialize LLM and embeddings
        self._llm = None
        self._embeddings = None

    @property
    def llm(self):
        """Lazy-load LLM."""
        if self._llm is None:
            self._llm = get_langchain_llm()
        return self._llm

    @property
    def embeddings(self):
        """Lazy-load embeddings."""
        if self._embeddings is None:
            self._embeddings = get_langchain_embeddings()
        return self._embeddings

    def send_message(self, chat_id: UUID, user_message: str) -> Dict[str, Any]:
        """
        Process message through RAG pipeline.

        Phase 1: Stub that returns a placeholder.
        Phase 2: Full implementation with retrieval and generation.

        Args:
            chat_id: UUID of the chat session
            user_message: User's question/message

        Returns:
            Dict with 'response' and 'sources' keys

        Raises:
            ValueError: If chat not found
        """
        chat = self.chat_repo.get_by_id(chat_id)
        if not chat:
            raise ValueError(f"Chat {chat_id} not found")

        # Phase 1: Placeholder implementation
        # Phase 2 will implement full RAG logic:
        # 1. Retrieve documents from vector store
        # 2. Build context from retrieved documents
        # 3. Generate response using LLM chain
        # 4. Save to database

        response_text = "[Phase 1 - LangChain RAG Stub] This is a placeholder response."

        # Save to database
        self.chat_repo.add_message(chat, sender="user", text=user_message)
        self.chat_repo.add_message(chat, sender="bot", text=response_text)
        self.db.commit()

        return {
            "response": response_text,
            "sources": [],
        }

    def _retrieve_documents(self, chat_id: UUID, query: str) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents from vector store.

        Phase 2: To be implemented.

        Args:
            chat_id: Chat session ID
            query: User query

        Returns:
            List of documents with metadata
        """
        # Phase 2 implementation
        raise NotImplementedError("Phase 2: Retrieval implementation")

    def _build_chain(self, chat_id: UUID):
        """
        Build RAG chain using LCEL.

        Phase 2: To be implemented.

        Args:
            chat_id: Chat session ID

        Returns:
            Callable chain for processing queries
        """
        # Phase 2 implementation
        raise NotImplementedError("Phase 2: Chain building")

    def _format_documents(self, docs: List[Dict]) -> str:
        """
        Format retrieved documents for prompt context.

        Args:
            docs: List of documents with metadata

        Returns:
            Formatted context string
        """
        if not docs:
            return ""

        context_parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.get("source", "Unknown")
            content = doc.get("content", "")
            context_parts.append(f"[Source {i}: {source}]\n{content}")

        return "\n\n".join(context_parts)
