# LangChain RAG Pipeline Migration Guide

**Date**: November 3, 2024
**Status**: Planning Phase
**Scope**: Gradual migration from manual RAG implementation to LangChain

---

## 📊 Current RAG Pipeline Analysis

### Current Architecture

The current RAG system is **manually implemented** with the following components:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Current Manual RAG                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Document Upload → PDF Processing → Chunking → Embeddings      │
│      (FastAPI)      (LlamaParse)   (Custom)  (Sentence- │
│                                              Transformers)      │
│           ↓                                       ↓             │
│      PostgreSQL ←───────────────────→ Weaviate Vector Store    │
│    (Document DB)                      (Semantic Search)         │
│           ↓                                                      │
│  Message Storage                                                 │
│  (Chat History)                                                  │
│           ↓                                       ↑             │
│  Query Handling → Manual Prompt → Gemini LLM ──┴─ Retrieved    │
│  (Custom Logic)    Building       (gemini-2.0    Context       │
│                                   -flash)                       │
│           ↓                                                      │
│  Response Generation & Storage                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Current Components

| Component | Location | Responsibility | Status |
|-----------|----------|-----------------|--------|
| **Document Upload** | `endpoints/documents.py` | File upload handling | ✅ Works |
| **PDF Processing** | `services/document_service.py` | Extract text/tables from PDFs | ✅ Works |
| **Chunking** | `services/document_service.py` | Split text into vectors | Manual |
| **Embeddings** | `core/services.py` | Generate embeddings (Sentence-Transformers) | Manual |
| **Vector Store** | `db/vector_store.py` | Weaviate collection management | Custom |
| **Chat Service** | `services/chat_service.py` | Message handling | Manual |
| **RAG Pipeline** | `services/rag_service.py` | Query→Context→Response flow | Manual |
| **LLM Integration** | `core/services.py` | Gemini API calls | Direct |
| **Chat History** | `db/repository.py` | Message persistence | SQLAlchemy |

### Current Pain Points

1. **Manual Prompt Engineering**: Prompt building done with string concatenation
2. **No Chain Abstraction**: Each request rebuilds the entire flow
3. **Limited Memory Management**: Chat history manually formatted for API
4. **No Built-in Tools**: Cannot easily add tools, agents, or advanced retrieval
5. **Verbose Code**: ~300+ lines of custom RAG logic
6. **Hard to Extend**: Adding new retrieval strategies requires code changes
7. **Limited Error Handling**: No built-in retry logic or error recovery
8. **No Observability**: Difficult to trace execution and debug

---

## 🎯 Benefits of LangChain Migration

### Direct Benefits

| Benefit | Current | With LangChain |
|---------|---------|----------------|
| **Prompt Management** | String concat | Templates + variables |
| **Chain Orchestration** | Manual, scattered | Declarative pipes |
| **Memory Handling** | Custom formatting | Built-in ConversationMemory |
| **Retrieval** | Custom Weaviate calls | Unified retriever interface |
| **LLM Integration** | Direct API calls | Unified ChatInterface |
| **Error Handling** | None | Retry, fallback, error callbacks |
| **Tool Support** | Not possible | Native agents + tools |
| **Monitoring** | Manual logging | Built-in callbacks |
| **Code Reusability** | Low | High (community chains) |

### Architecture Improvements

```
┌─────────────────────────────────────────────────────────────────┐
│              LangChain-Based RAG (Future)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Document Upload → LangChain Document Loaders                   │
│                          ↓                                      │
│                  RecursiveCharacterTextSplitter                 │
│                          ↓                                      │
│              LangChain Embeddings (abstracted)                  │
│                          ↓                                      │
│           PostgreSQL + Weaviate (via VectorStore)              │
│                          ↓                                      │
│        LangChain Retriever (unified interface)                  │
│                          ↓                                      │
│        RAGChain (LangChain LCEL pipe)                           │
│           ├─ Prompt Template                                    │
│           ├─ Chat History Memory                                │
│           ├─ Retrieved Context                                  │
│           └─ Chat Output Parser                                 │
│                          ↓                                      │
│              Gemini LLM (via LangChain)                         │
│                          ↓                                      │
│            Response + Sources (structured)                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Migration Strategy: 3-Phase Approach

### Phase 1: Foundation (1-2 weeks)
**Goal**: Set up LangChain infrastructure alongside existing system

**Tasks**:
1. Add LangChain to `requirements.txt`
2. Create `app/core/langchain_setup.py`:
   - Initialize LangChain ChatGoogleGenerativeAI
   - Create LangChain embeddings wrapper
   - Set up prompt templates
3. Create new service: `app/modules/askai/services/langchain_rag_service.py`
   - Implement basic RAGChain
   - Create retriever from Weaviate
   - Build simple prompt template
4. Add feature flag for migration (use old or new pipeline)
5. Write unit tests for new components

**No Breaking Changes**: Old pipeline continues to work

**Output**:
- LangChain infrastructure ready
- Feature flag to toggle between old/new
- Passing tests for new RAGChain

### Phase 2: Core RAG Integration (2-3 weeks)
**Goal**: Migrate RAG pipeline to LangChain chains

**Tasks**:
1. Implement `LangChainRAGService`:
   - Use LangChain ChatGoogleGenerativeAI
   - Implement conversation memory (ConversationBufferMemory)
   - Build retrieval chain (SimpleRetrieverChain → Custom RAGChain)
   - Structured output parsing
2. Create prompt templates:
   - System prompt with context
   - Few-shot examples
   - Output formatting instructions
3. Migration compatibility layer:
   - Map old response format to new
   - Ensure API contracts don't break
4. Add retrieval options:
   - BM25 (full-text search alternative)
   - Similarity with score threshold
   - MMR (Maximal Marginal Relevance)

**Testing**: Parallel testing with both pipelines

**Output**:
- Functional LangChain RAG service
- Backward-compatible API responses
- Switchable via feature flag

### Phase 3: Document Processing Pipeline (2 weeks)
**Goal**: Replace document processing with LangChain document loaders/splitters

**Tasks**:
1. Create `LangChainDocumentProcessor`:
   - Use LangChain document loaders
   - Replace custom PDF splitting with RecursiveCharacterTextSplitter
   - Standardize metadata handling
2. Update document upload endpoint:
   - Support multiple file types (PDF, markdown, text, etc.)
   - Use LangChain's built-in loaders where applicable
3. Migrate embedding generation:
   - Use LangChain embedding interface
   - Support multiple embedding models (swappable)
4. Optimize chunking:
   - Experiment with chunk sizes
   - Implement semantic chunking
5. Update tests for document processing

**Output**:
- LangChain-based document processing
- Support for multiple file formats
- Pluggable embedding models

### Phase 4: Advanced Features (3-4 weeks) [Optional]
**Goal**: Add LangChain advanced capabilities

**Tasks**:
1. Implement agents:
   - Add tools (web search, calculator, code execution)
   - Create agent executor for complex queries
2. Add memory options:
   - Conversation summary memory (for long chats)
   - Entity-based memory (important entities tracking)
   - MongoDB-backed memory (persistent)
3. Implement retrievers:
   - Multi-query retriever
   - ParentDocument retriever
   - Ensemble retrievers (combine multiple sources)
4. Add observability:
   - LangSmith integration for debugging
   - Custom callbacks for logging
   - Performance metrics collection
5. Create admin tools:
   - Batch document processing
   - Re-embedding capability
   - Performance analytics dashboard

**Output**:
- Advanced agent capabilities
- Better memory management
- Production observability
- Admin panel features

---

## 🛠️ Implementation Details

### Phase 1: Foundation Setup

#### 1.1 Requirements Update

Add to `requirements.txt`:
```
langchain==0.1.11
langchain-google-genai==0.0.11
langchain-community==0.0.11
```

#### 1.2 Create `app/core/langchain_setup.py`

```python
from langchain.chat_models import ChatGoogleGenerativeAI
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import BaseMessage
from app.config import settings

# Initialize ChatGoogleGenerativeAI
def get_langchain_llm():
    """Get configured LangChain LLM."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.7,
        convert_system_message_to_human=True,
    )

# Initialize embeddings (drop-in replacement for SentenceTransformers)
def get_langchain_embeddings():
    """Get configured LangChain embeddings."""
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"show_progress_bar": True, "batch_size": 32},
    )

# Create prompt templates
RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful AI assistant that answers questions based on provided document context.

INSTRUCTIONS:
1. Answer using the information in the context above
2. Be specific and cite which sources support your answer
3. If the context doesn't contain the answer, feel free to add information from other sources, but clearly state that
4. Be concise but thorough
5. Use GitHub markdown formatting"""),
    ("human", """CONTEXT:
{context}

USER QUESTION: {question}""")
])

# Create memory wrapper
class ChatHistoryMemory(ConversationBufferMemory):
    """Wrapper for chat history with custom serialization."""

    def get_history_for_gemini(self):
        """Convert to Gemini API format."""
        messages = self.chat_memory.messages
        return [
            {
                "role": "model" if msg.type == "ai" else "user",
                "parts": [{"text": msg.content}]
            }
            for msg in messages
        ]
```

#### 1.3 Create `app/modules/askai/services/langchain_rag_service.py`

```python
from uuid import UUID
from typing import Dict, List
from langchain.chains import RetrievalQA
from langchain.schema import Document
from sqlalchemy.orm import Session
from app.core.langchain_setup import get_langchain_llm, RAG_PROMPT
from app.db.vector_store import VectorStoreManager
from app.modules.askai.db.repository import ChatRepository

class LangChainRAGService:
    """RAG service using LangChain chains."""

    def __init__(self, vector_store: VectorStoreManager, db: Session):
        self.vector_store = vector_store
        self.db = db
        self.llm = get_langchain_llm()
        self.chat_repo = ChatRepository(db)

    def send_message(self, chat_id: UUID, user_message: str) -> Dict:
        """Process message using LangChain RAG chain."""
        chat = self.chat_repo.get_by_id(chat_id)
        if not chat:
            raise ValueError("Chat not found")

        # Get retriever from Weaviate
        collection = self.vector_store.get_or_create_collection(str(chat_id))
        retriever = self._create_retriever(collection)

        # Create RAG chain
        rag_chain = (RAG_PROMPT | self.llm)

        # Retrieve relevant documents
        retrieved_docs = retriever.get_relevant_documents(user_message)
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])

        # Generate response
        response = rag_chain.invoke({
            "context": context,
            "question": user_message
        })

        # Save to database
        self.chat_repo.add_message(chat, sender="user", text=user_message)
        self.chat_repo.add_message(chat, sender="bot", text=response.content)
        self.db.commit()

        return {
            "response": response.content,
            "sources": retrieved_docs
        }

    def _create_retriever(self, collection):
        """Create retriever from Weaviate collection."""
        # Implement as LangChain retriever
        pass
```

#### 1.4 Create Feature Flag

Add to `app/config.py`:
```python
class Settings:
    # ... existing config ...
    USE_LANGCHAIN_RAG: bool = False  # Toggle for migration
```

---

### Phase 2: Core RAG Integration

#### 2.1 Implement ConversationMemory

```python
from langchain.memory import ConversationBufferMemory
from app.modules.askai.db.models import Message

class DatabaseConversationMemory(ConversationBufferMemory):
    """Memory that reads/writes from SQLAlchemy database."""

    def __init__(self, chat_repo, chat_id):
        super().__init__()
        self.chat_repo = chat_repo
        self.chat_id = chat_id
        self._load_from_db()

    def _load_from_db(self):
        """Load chat history from database."""
        messages = self.chat_repo.get_chat_messages(self.chat_id)
        for msg in messages[-10:]:  # Last 10 messages
            if msg.sender == "user":
                self.chat_memory.add_user_message(msg.text)
            else:
                self.chat_memory.add_ai_message(msg.text)
```

#### 2.2 Implement Custom Retriever

```python
from langchain.schema import BaseRetriever, Document

class WeaviateRetriever(BaseRetriever):
    """Retriever that wraps Weaviate vector store."""

    def __init__(self, vector_store, collection, top_k=5):
        self.vector_store = vector_store
        self.collection = collection
        self.top_k = top_k

    def _get_relevant_documents(self, query):
        """Get documents from Weaviate."""
        results = self.vector_store.query(
            self.collection,
            query,
            n_results=self.top_k
        )

        documents = []
        for doc, meta, score in results:
            documents.append(Document(
                page_content=doc,
                metadata={**meta, "score": score}
            ))
        return documents

    async def _aget_relevant_documents(self, query):
        """Async version."""
        return self._get_relevant_documents(query)
```

#### 2.3 Build Complete RAG Chain

```python
from langchain.chains import LLMChain
from langchain.schema.runnable import RunnablePassthrough

class RAGChain:
    """Complete RAG pipeline using LangChain LCEL."""

    def __init__(self, llm, retriever, prompt_template):
        self.llm = llm
        self.retriever = retriever
        self.prompt = prompt_template

        # Build chain using LCEL (LangChain Expression Language)
        self.chain = (
            {
                "context": self.retriever | self._format_docs,
                "question": RunnablePassthrough()
            }
            | self.prompt
            | self.llm
        )

    def _format_docs(self, docs):
        """Format documents for prompt."""
        return "\n\n".join([
            f"[Source: {d.metadata.get('source')}]\n{d.page_content}"
            for d in docs
        ])

    def invoke(self, query):
        """Run the chain."""
        return self.chain.invoke(query)
```

---

### Phase 3: Document Processing

#### 3.1 Replace Document Splitting

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

class LangChainDocumentProcessor:
    """Document processing using LangChain."""

    def __init__(self, embedding_model):
        self.embedding_model = embedding_model
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )

    def process_pdf(self, file_path: str, doc_id: str) -> List[Dict]:
        """Process PDF using LangChain."""
        from langchain.document_loaders import PyPDFLoader

        loader = PyPDFLoader(file_path)
        documents = loader.load()

        # Split documents
        chunks = self.splitter.split_documents(documents)

        # Add metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata["doc_id"] = doc_id
            chunk.metadata["chunk_index"] = i

        return chunks
```

#### 3.2 Update Embeddings Interface

```python
from langchain.embeddings.base import Embeddings

class LangChainEmbeddingsWrapper(Embeddings):
    """Wrapper for existing embedding model."""

    def __init__(self, model):
        self.model = model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents."""
        return self.model.encode(texts, show_progress_bar=True)

    def embed_query(self, text: str) -> List[float]:
        """Embed query."""
        return self.model.encode(text).tolist()
```

---

## 📋 Migration Checklist

### Phase 1: Foundation
- [ ] Add LangChain to requirements.txt
- [ ] Create `app/core/langchain_setup.py` with LLM/embeddings initialization
- [ ] Create `app/modules/askai/services/langchain_rag_service.py`
- [ ] Add `USE_LANGCHAIN_RAG` feature flag
- [ ] Write unit tests for LangChain components
- [ ] Update CLAUDE.md with LangChain info
- [ ] Document configuration requirements

### Phase 2: Core RAG
- [ ] Implement DatabaseConversationMemory
- [ ] Implement WeaviateRetriever
- [ ] Build RAGChain with LCEL
- [ ] Update `send_message_to_chat()` to use feature flag
- [ ] Test response quality (same or better)
- [ ] Add integration tests
- [ ] Document new prompts and chains

### Phase 3: Document Processing
- [ ] Replace custom PDF splitting with RecursiveCharacterTextSplitter
- [ ] Create LangChainDocumentProcessor
- [ ] Test document processing quality
- [ ] Support multiple file types (markdown, text, docx)
- [ ] Update document upload endpoint
- [ ] Performance benchmarking

### Phase 4: Advanced Features (Optional)
- [ ] Implement agents and tools
- [ ] Add memory variants
- [ ] Build multi-retriever ensemble
- [ ] Integrate LangSmith
- [ ] Create admin dashboard

---

## ⚠️ Considerations & Risks

### Compatibility
- **Risk**: LangChain API changes
- **Mitigation**: Pin version numbers, gradual updates
- **Plan**: Keep abstraction layer stable

### Performance
- **Risk**: Additional overhead from LangChain abstraction
- **Mitigation**: Benchmark both implementations
- **Plan**: Profile critical paths

### Learning Curve
- **Risk**: Team unfamiliar with LangChain
- **Mitigation**: Documentation, training
- **Plan**: Code reviews, pair programming

### State Management
- **Risk**: LangChain memory vs DB consistency
- **Mitigation**: Write all messages to DB, use as source of truth
- **Plan**: LangChain memory only for current session

---

## 📚 Recommended LangChain Patterns

### 1. Use LCEL (LangChain Expression Language)
Modern, declarative way to build chains:
```python
chain = prompt | llm | output_parser
```

### 2. Separate Concerns
- **Retriever**: Get relevant documents
- **Prompt**: Format input + context
- **LLM**: Generate response
- **Parser**: Structure output

### 3. Memory Best Practices
- Load from DB on chat init
- Save all messages to DB immediately
- Use LangChain memory for context only
- Implement selective history (last N messages)

### 4. Error Handling
```python
from langchain.llms.base import LLMError

try:
    response = chain.invoke(input)
except LLMError as e:
    # Handle LLM-specific errors
    fallback_response = get_fallback_response()
```

### 5. Monitoring
```python
from langchain.callbacks import StdOutCallbackHandler

handler = StdOutCallbackHandler()
response = chain.invoke(input, callbacks=[handler])
```

---

## 🔄 Parallel Running Strategy

### Week 1-2: Foundation + Initial Testing
- Deploy Phase 1 to dev environment
- Run unit tests only
- No user-facing changes

### Week 3-4: Core RAG Integration
- Deploy Phase 2 to staging
- Run both pipelines in parallel (feature flag)
- A/B test with internal users only
- Compare response quality and performance

### Week 5-6: Document Processing
- Deploy Phase 3 to staging
- Test with all document types
- Performance benchmark
- Optimize chunking parameters

### Week 7+: Gradual Rollout
- Enable LangChain for 10% of users
- Monitor quality metrics
- Increase to 100% if all good
- Keep old code as fallback for 1 month

---

## 📊 Success Metrics

Track these before and after migration:

| Metric | Target | Notes |
|--------|--------|-------|
| **Response Quality** | Same or better | Via A/B testing |
| **Response Latency** | <2s p95 | End-to-end timing |
| **Hallucination Rate** | <5% | Manual evaluation |
| **Code Complexity** | -30% LOC | Lines of code |
| **Test Coverage** | >80% | Unit + integration |
| **Documentation** | 100% | All components |

---

## 🎓 Learning Resources

### Official Documentation
- [LangChain Documentation](https://python.langchain.com/)
- [LCEL Guide](https://python.langchain.com/docs/expression_language/)
- [Retrievers](https://python.langchain.com/docs/modules/data_connection/retrievers/)

### Key Concepts
- **Chain**: Sequence of operations
- **LCEL**: Declarative syntax for chains
- **Retriever**: Interface for document retrieval
- **Memory**: Chat history management
- **Callbacks**: Hooks for logging/monitoring
- **Agent**: Autonomous decision-making system

### Community Examples
- [LangChain Examples Repo](https://github.com/langchain-ai/langchain/tree/master/docs/docs/use_cases)
- [LangSmith Documentation](https://docs.smith.langchain.com/)

---

## 🚀 Next Steps

1. **Immediate** (This week):
   - Review this guide with team
   - Plan Phase 1 sprint
   - Assign ownership

2. **Short-term** (Next 2 weeks):
   - Implement Phase 1 foundation
   - Set up feature flag infrastructure
   - Create testing harness

3. **Medium-term** (Weeks 3-6):
   - Execute Phase 2 & 3
   - Parallel testing with both pipelines
   - Performance benchmarking

4. **Long-term** (Week 7+):
   - Gradual rollout to users
   - Monitor quality metrics
   - Plan Phase 4 advanced features

---

## 📝 Questions for the Team

1. **Embedding Model**: Keep Sentence-Transformers or switch to OpenAI embeddings?
2. **Chat Memory**: Store all history or implement summary memory?
3. **Retrieval Strategy**: Simple similarity or implement MMR?
4. **LLM Model**: Stay with Gemini 2.0 Flash or explore alternatives?
5. **Observability**: Use LangSmith for production debugging?
6. **Tool Support**: Do we need agent capabilities with tools?

---

**Status**: Ready for team discussion and Phase 1 planning
**Estimated Total Effort**: 8-12 weeks for full migration
**Recommended Start**: Next sprint
