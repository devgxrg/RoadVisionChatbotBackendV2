# LangChain Implementation Roadmap

**Timeline**: 8-12 weeks | **Effort**: ~300-400 hours | **Risk**: Low (parallel deployment)

---

## Quick Summary

This document outlines the **step-by-step implementation** to migrate from manual RAG to LangChain-based pipeline. It complements the detailed migration guide with concrete tasks, timelines, and deliverables.

---

## 📅 Timeline Overview

```
Week 1-2    │ Phase 1: Foundation
            │ ├─ LangChain setup
            │ ├─ Feature flag infrastructure
            │ └─ Unit tests
            │
Week 3-4    │ Phase 2: Core RAG
            │ ├─ Memory implementation
            │ ├─ Retriever wrapper
            │ ├─ RAG chain building
            │ └─ A/B testing setup
            │
Week 5-6    │ Phase 3: Document Processing
            │ ├─ Text splitter migration
            │ ├─ Multi-format support
            │ ├─ Benchmark & optimize
            │ └─ Edge case testing
            │
Week 7-8    │ Phase 4 (Optional): Advanced Features
            │ ├─ Agents & tools
            │ ├─ Memory variants
            │ ├─ Observability
            │ └─ Admin tools
            │
Week 9-12   │ Production Rollout
            │ ├─ Gradual user rollout (10% → 50% → 100%)
            │ ├─ Monitoring & optimization
            │ ├─ Fallback strategy
            │ └─ Documentation update
```

---

## Phase 1: Foundation (Weeks 1-2)

### Sprint 1.1: Setup & Dependencies

**Duration**: 2 days
**Owner**: DevOps/Backend Lead

#### Tasks

1. **Update Dependencies**
   - [ ] Add to `requirements.txt`:
     ```
     langchain==0.1.11
     langchain-google-genai==0.0.11
     langchain-community==0.0.11
     langchain-core==0.1.17
     ```
   - [ ] Run `pip install -r requirements.txt`
   - [ ] Test imports in isolation
   - [ ] Document version constraints

2. **Create Feature Flag System**
   - [ ] Add `USE_LANGCHAIN_RAG` to `app/config.py`
   - [ ] Create `app/utils/feature_flags.py` module:
     ```python
     def use_langchain_rag():
         return settings.USE_LANGCHAIN_RAG
     ```
   - [ ] Update endpoints to check flag
   - [ ] Create environment configuration

3. **Setup LangChain Infrastructure**
   - [ ] Create `app/core/langchain_config.py`
   - [ ] Create `app/core/langchain_components.py`
   - [ ] Add to `.env`:
     ```
     LANGCHAIN_VERBOSE=true  # For debugging
     LANGCHAIN_API_KEY=[optional for LangSmith]
     ```

**Deliverables**:
- ✅ LangChain installed and tested
- ✅ Feature flag infrastructure in place
- ✅ Configuration files created
- ✅ Team can switch between implementations

**PR Review Checklist**:
- [ ] No breaking changes to existing code
- [ ] All imports tested
- [ ] Feature flag works both ways
- [ ] Documentation updated

---

### Sprint 1.2: LangChain Components

**Duration**: 3 days
**Owner**: Backend Engineer

#### Tasks

1. **Create LLM Wrapper** (`app/core/langchain_components.py`)
   ```python
   from langchain_google_genai import ChatGoogleGenerativeAI

   def get_langchain_llm():
       return ChatGoogleGenerativeAI(
           model="gemini-2.0-flash",
           google_api_key=settings.GOOGLE_API_KEY,
           temperature=0.7,
           top_p=0.95,
           max_tokens=2048,
       )
   ```
   - [ ] Test LLM initialization
   - [ ] Test basic invocation
   - [ ] Verify response format
   - [ ] Test error handling

2. **Create Embeddings Wrapper**
   ```python
   from langchain_community.embeddings import HuggingFaceEmbeddings

   def get_langchain_embeddings():
       return HuggingFaceEmbeddings(
           model_name="all-MiniLM-L6-v2",
       )
   ```
   - [ ] Test embeddings generation
   - [ ] Compare with existing SentenceTransformers
   - [ ] Performance benchmark
   - [ ] Dimension verification (384)

3. **Create Prompt Templates** (`app/core/langchain_prompts.py`)
   ```python
   from langchain_core.prompts import ChatPromptTemplate

   RAG_PROMPT = ChatPromptTemplate.from_messages([
       ("system", "..."),
       ("human", "CONTEXT: {context}\n\nQUESTION: {question}")
   ])
   ```
   - [ ] Define system prompt
   - [ ] Create template variables
   - [ ] Test template rendering
   - [ ] Verify placeholders work

4. **Unit Tests** (`tests/unit/test_langchain_components.py`)
   - [ ] Test LLM initialization
   - [ ] Test embeddings generation
   - [ ] Test prompt template rendering
   - [ ] Test error handling
   - [ ] Achieve 90%+ coverage

**Deliverables**:
- ✅ LLM wrapper with tests
- ✅ Embeddings wrapper with tests
- ✅ Prompt templates with tests
- ✅ 100 lines of test code
- ✅ All tests passing

**PR Review Checklist**:
- [ ] Code follows project style
- [ ] Tests are comprehensive
- [ ] Error cases covered
- [ ] Documentation included
- [ ] No external API calls in tests

---

### Sprint 1.3: RAG Service Skeleton

**Duration**: 2 days
**Owner**: Backend Engineer

#### Tasks

1. **Create Service Structure**
   ```
   app/modules/askai/services/
   ├── langchain_rag_service.py      # New
   ├── langchain_memory.py           # New
   ├── langchain_retriever.py        # New
   ├── rag_service.py                # Existing (unchanged)
   └── ...
   ```
   - [ ] Create empty service files
   - [ ] Add docstrings
   - [ ] Define class signatures
   - [ ] Add type hints

2. **Create Service Classes** (stubs)
   ```python
   class LangChainRAGService:
       def __init__(self, vector_store, db):
           pass

       def send_message(self, chat_id: UUID, message: str) -> Dict:
           """Process message using LangChain RAG."""
           raise NotImplementedError
   ```
   - [ ] Create class with __init__
   - [ ] Define all public methods
   - [ ] Add comprehensive docstrings
   - [ ] Add type hints

3. **Create Dependency Injection** (`app/modules/askai/dependencies.py`)
   ```python
   def get_langchain_rag_service(
       db: Session = Depends(get_db_session)
   ) -> LangChainRAGService:
       return LangChainRAGService(vector_store, db)
   ```
   - [ ] Create dependency function
   - [ ] Test dependency injection
   - [ ] Verify integration with FastAPI

**Deliverables**:
- ✅ Service file structure created
- ✅ Class signatures defined
- ✅ Dependency injection ready
- ✅ Ready for Phase 2 implementation

---

### Sprint 1.4: Feature Flag Integration

**Duration**: 1.5 days
**Owner**: Backend Engineer

#### Tasks

1. **Update Chat Endpoint** (`endpoints/chats.py`)
   ```python
   def send_message(
       chat_id: UUID,
       message: str,
       db: Session = Depends(get_db_session),
       langchain_service = Depends(get_langchain_rag_service),
       old_service = Depends(get_rag_service),
   ):
       if settings.USE_LANGCHAIN_RAG:
           return langchain_service.send_message(chat_id, message)
       else:
           return old_service.send_message(chat_id, message)
   ```
   - [ ] Add feature flag check
   - [ ] Both services available
   - [ ] Test flag switching
   - [ ] No errors with either path

2. **Create A/B Testing Framework** (prep for Phase 2)
   ```python
   # tests/integration/test_rag_comparison.py
   def test_both_services_produce_output():
       """Both RAG services should work."""
       pass
   ```
   - [ ] Create comparison test structure
   - [ ] Document comparison metrics
   - [ ] Ready for Phase 2 testing

**Deliverables**:
- ✅ Feature flag integrated
- ✅ Both code paths work
- ✅ Clean switch possible
- ✅ Testing framework ready

---

## Phase 2: Core RAG Integration (Weeks 3-4)

### Sprint 2.1: Memory Implementation

**Duration**: 3 days
**Owner**: Backend Engineer

#### Tasks

1. **Implement Database Memory** (`app/modules/askai/services/langchain_memory.py`)
   ```python
   class DatabaseConversationMemory(ConversationBufferMemory):
       def __init__(self, chat_repo, chat_id):
           super().__init__()
           self.chat_repo = chat_repo
           self.chat_id = chat_id
           self.load_history()

       def load_history(self):
           """Load last 10 messages from DB."""
           messages = self.chat_repo.get_messages(
               self.chat_id,
               limit=10
           )
           for msg in messages:
               if msg.sender == "user":
                   self.chat_memory.add_user_message(msg.text)
               else:
                   self.chat_memory.add_ai_message(msg.text)
   ```
   - [ ] Implement memory class
   - [ ] Test loading from DB
   - [ ] Test message addition
   - [ ] Test history truncation

2. **Write Memory Tests** (`tests/unit/test_langchain_memory.py`)
   - [ ] Test loading empty chat
   - [ ] Test loading with messages
   - [ ] Test message limits
   - [ ] Test message ordering
   - [ ] Mock database calls

3. **Memory Configuration** (`app/core/langchain_config.py`)
   ```python
   MEMORY_CONFIG = {
       "memory_type": "buffer",
       "k": 10,  # Last 10 messages
       "return_messages": True,
   }
   ```
   - [ ] Define config constants
   - [ ] Make tunable via env
   - [ ] Document options

**Deliverables**:
- ✅ DatabaseConversationMemory working
- ✅ Comprehensive tests
- ✅ Configuration done
- ✅ Can load/save chat history

---

### Sprint 2.2: Retriever Implementation

**Duration**: 3 days
**Owner**: Backend Engineer

#### Tasks

1. **Create Weaviate Retriever** (`app/modules/askai/services/langchain_retriever.py`)
   ```python
   from langchain_core.retrievers import BaseRetriever
   from langchain_core.documents import Document

   class WeaviateRetriever(BaseRetriever):
       def __init__(self, vector_store, collection, top_k=5):
           self.vector_store = vector_store
           self.collection = collection
           self.top_k = top_k

       def _get_relevant_documents(self, query: str):
           """Retrieve documents from Weaviate."""
           results = self.vector_store.query(
               self.collection,
               query,
               n_results=self.top_k
           )

           documents = []
           for doc_text, metadata, score in results:
               documents.append(Document(
                   page_content=doc_text,
                   metadata={
                       **metadata,
                       "relevance_score": score
                   }
               ))
           return documents

       async def _aget_relevant_documents(self, query: str):
           return self._get_relevant_documents(query)
   ```
   - [ ] Implement retriever class
   - [ ] Test retrieval works
   - [ ] Test document formatting
   - [ ] Test metadata passing

2. **Write Retriever Tests**
   - [ ] Test with empty collection
   - [ ] Test with documents
   - [ ] Test result formatting
   - [ ] Test metadata preservation
   - [ ] Mock Weaviate calls

3. **Test with Real Weaviate** (integration test)
   - [ ] Create test collection
   - [ ] Add test documents
   - [ ] Verify retrieval accuracy
   - [ ] Clean up after tests

**Deliverables**:
- ✅ WeaviateRetriever working
- ✅ Unit tests passing
- ✅ Integration tests passing
- ✅ Ready for chain building

---

### Sprint 2.3: RAG Chain Implementation

**Duration**: 3 days
**Owner**: Backend Engineer

#### Tasks

1. **Build RAG Chain** (`app/modules/askai/services/langchain_rag_service.py`)
   ```python
   from langchain_core.runnables import RunnablePassthrough
   from langchain_core.output_parsers import StrOutputParser

   class LangChainRAGService:
       def __init__(self, vector_store, db):
           self.vector_store = vector_store
           self.db = db
           self.llm = get_langchain_llm()
           self.chat_repo = ChatRepository(db)

       def build_chain(self, chat_id: UUID):
           """Build RAG chain for chat."""
           collection = self.vector_store.get_or_create_collection(
               str(chat_id)
           )
           retriever = WeaviateRetriever(
               self.vector_store,
               collection,
               top_k=settings.RAG_TOP_K
           )

           prompt = get_rag_prompt()

           # Build chain using LCEL
           chain = (
               {
                   "context": retriever | self._format_docs,
                   "question": RunnablePassthrough()
               }
               | prompt
               | self.llm
               | StrOutputParser()
           )

           return chain

       def _format_docs(self, docs: List[Document]) -> str:
           """Format documents for prompt."""
           return "\n\n".join([
               f"[Source {i+1}: {d.metadata.get('source')}]\n{d.page_content}"
               for i, d in enumerate(docs)
           ])

       def send_message(self, chat_id: UUID, message: str) -> Dict:
           """Process message through RAG pipeline."""
           chat = self.chat_repo.get_by_id(chat_id)
           if not chat:
               raise ValueError("Chat not found")

           chain = self.build_chain(chat_id)
           response = chain.invoke(message)

           # Save to DB
           self.chat_repo.add_message(chat, "user", message)
           self.chat_repo.add_message(chat, "bot", response)
           self.db.commit()

           return {
               "response": response,
               "sources": [],  # Extract from metadata
           }
   ```
   - [ ] Implement RAG chain
   - [ ] Test chain invocation
   - [ ] Test response format
   - [ ] Test database saving

2. **Write RAG Tests**
   - [ ] Test chain building
   - [ ] Test message processing
   - [ ] Test response quality
   - [ ] Test error handling
   - [ ] Mock all dependencies

3. **Compare with Old Implementation**
   - [ ] Response format matches
   - [ ] Sources extracted correctly
   - [ ] Chat history saved correctly
   - [ ] No data loss

**Deliverables**:
- ✅ RAG chain fully working
- ✅ All tests passing
- ✅ Compatible with existing API
- ✅ Ready for A/B testing

---

### Sprint 2.4: A/B Testing & Validation

**Duration**: 2 days
**Owner**: QA Engineer + Backend Lead

#### Tasks

1. **Create A/B Testing Harness** (`tests/integration/test_rag_ab.py`)
   ```python
   def test_both_services_same_output():
       """Both services should produce same quality output."""
       test_cases = [
           ("What is AI?", "test_chat_1"),
           ("Explain machine learning", "test_chat_2"),
       ]

       for query, chat_id in test_cases:
           old_response = old_rag.send_message(chat_id, query)
           new_response = langchain_rag.send_message(chat_id, query)

           assert len(new_response["response"]) > 0
           # Quality should be similar
   ```
   - [ ] Create test cases
   - [ ] Run both implementations
   - [ ] Compare outputs
   - [ ] Document differences

2. **Performance Benchmarking**
   - [ ] Time first message (cold start)
   - [ ] Time subsequent messages
   - [ ] Memory usage comparison
   - [ ] Token usage comparison
   - [ ] Document metrics

3. **Manual Testing** (internal only)
   - [ ] Test with 3-5 team members
   - [ ] Compare response quality
   - [ ] Check for hallucinations
   - [ ] Verify source attribution
   - [ ] Document feedback

**Deliverables**:
- ✅ A/B testing framework
- ✅ Performance benchmarks
- ✅ Comparison documentation
- ✅ Go/no-go decision for Phase 3

---

## Phase 3: Document Processing (Weeks 5-6)

### Sprint 3.1: Text Splitting Migration

**Duration**: 2 days
**Owner**: Backend Engineer

#### Tasks

1. **Create LangChain Document Processor** (`app/modules/askai/services/langchain_document_service.py`)
   ```python
   from langchain.document_loaders import PyPDFLoader
   from langchain.text_splitter import RecursiveCharacterTextSplitter

   class LangChainDocumentProcessor:
       def __init__(self, embedding_model):
           self.embedding_model = embedding_model
           self.splitter = RecursiveCharacterTextSplitter(
               chunk_size=1000,
               chunk_overlap=200,
               separators=["\n\n", "\n", " ", ""]
           )

       def process_pdf(self, file_path: str, doc_id: str, filename: str):
           """Process PDF using LangChain."""
           loader = PyPDFLoader(file_path)
           documents = loader.load()

           chunks = self.splitter.split_documents(documents)

           # Add metadata
           for i, chunk in enumerate(chunks):
               chunk.metadata.update({
                   "doc_id": doc_id,
                   "chunk_index": i,
                   "filename": filename,
                   "source": filename,
               })

           return chunks
   ```
   - [ ] Implement document processor
   - [ ] Test PDF splitting
   - [ ] Compare with old splitting
   - [ ] Verify chunk sizes

2. **Write Document Tests**
   - [ ] Test with various PDFs
   - [ ] Test metadata preservation
   - [ ] Test chunk boundaries
   - [ ] Test edge cases (empty, large files)

**Deliverables**:
- ✅ LangChain document processor working
- ✅ Tests passing
- ✅ Compared with old approach

---

### Sprint 3.2: Multi-Format Support

**Duration**: 2 days
**Owner**: Backend Engineer

#### Tasks

1. **Add Multiple Loaders**
   ```python
   def process_document(self, file_path: str, file_type: str):
       if file_type == "pdf":
           loader = PyPDFLoader(file_path)
       elif file_type == "txt":
           loader = TextLoader(file_path)
       elif file_type == "markdown":
           loader = TextLoader(file_path)
       else:
           raise ValueError(f"Unsupported type: {file_type}")

       documents = loader.load()
       return self.splitter.split_documents(documents)
   ```
   - [ ] Support PDF ✅
   - [ ] Support TXT ✅
   - [ ] Support Markdown
   - [ ] Test each format

2. **Update Upload Endpoint**
   - [ ] Accept multiple file types
   - [ ] Auto-detect format
   - [ ] Process accordingly
   - [ ] Test all types

**Deliverables**:
- ✅ Multi-format document support
- ✅ All tests passing
- ✅ Updated endpoint working

---

### Sprint 3.3: Performance Optimization

**Duration**: 2 days
**Owner**: Backend Engineer

#### Tasks

1. **Benchmark Chunk Sizes**
   ```python
   TEST_CHUNK_SIZES = [512, 1024, 1500, 2000]

   for size in TEST_CHUNK_SIZES:
       processor = LangChainDocumentProcessor(
           splitter_config={"chunk_size": size}
       )
       # Measure retrieval quality
       # Measure latency
       # Measure cost
   ```
   - [ ] Test different chunk sizes
   - [ ] Measure retrieval quality
   - [ ] Measure token usage
   - [ ] Choose optimal size

2. **Optimize Overlap**
   ```python
   TEST_OVERLAPS = [0, 100, 200, 300, 500]

   for overlap in TEST_OVERLAPS:
       # Measure retrieval quality
       # Measure duplicate content
   ```
   - [ ] Test different overlaps
   - [ ] Measure document continuity
   - [ ] Choose optimal overlap

3. **Final Benchmarking**
   - [ ] Compare old vs new splitting
   - [ ] Measure indexing time
   - [ ] Measure retrieval quality
   - [ ] Document optimal settings

**Deliverables**:
- ✅ Performance benchmarks
- ✅ Optimal chunk parameters
- ✅ Configuration documented

---

## Phase 4: Advanced Features (Optional, Weeks 7-8)

### Sprint 4.1: Agents & Tools

**Duration**: 3 days
**Owner**: Backend Engineer

#### Tasks

1. **Create Basic Tools**
   ```python
   from langchain.tools import tool

   @tool
   def web_search(query: str) -> str:
       """Search the web for information."""
       return search_engine.search(query)

   @tool
   def calculate(expression: str) -> str:
       """Evaluate a mathematical expression."""
       return str(eval(expression))
   ```

2. **Create Agent**
   ```python
   from langchain.agents import AgentExecutor, create_openai_tools_agent

   agent = create_openai_tools_agent(
       llm,
       tools=[web_search, calculate],
       prompt=agent_prompt
   )

   executor = AgentExecutor.from_agent_and_tools(
       agent=agent,
       tools=tools,
       verbose=True
   )
   ```

3. **Integration Tests**
   - [ ] Test agent with tools
   - [ ] Test tool invocation
   - [ ] Test error handling

---

### Sprint 4.2: Observability

**Duration**: 2 days
**Owner**: Backend Engineer

#### Tasks

1. **Add LangSmith Integration**
   ```python
   import os
   os.environ["LANGCHAIN_TRACING_V2"] = "true"
   os.environ["LANGCHAIN_PROJECT"] = "langchain-rag"
   ```

2. **Custom Callbacks**
   ```python
   from langchain.callbacks import BaseCallbackHandler

   class LoggingHandler(BaseCallbackHandler):
       def on_chain_start(self, serialized, inputs, **kwargs):
           logger.info(f"Chain started with {inputs}")
   ```

---

## Phase 5: Production Rollout (Weeks 9-12)

### Sprint 5.1: Staged Rollout

**Duration**: 2 days
**Owner**: DevOps + Backend Lead

#### Tasks

1. **Week 9: 10% Rollout**
   - [ ] Enable for 10% of users
   - [ ] Monitor error rate
   - [ ] Monitor response quality
   - [ ] Check performance metrics

2. **Week 10: 50% Rollout**
   - [ ] Increase to 50% if metrics good
   - [ ] Continue monitoring
   - [ ] Gather user feedback

3. **Week 11: 100% Rollout**
   - [ ] Full rollout
   - [ ] Keep old code as fallback
   - [ ] Monitor for 1 week

4. **Week 12: Cleanup**
   - [ ] Remove feature flag
   - [ ] Remove old RAG code
   - [ ] Update documentation

---

## 📋 Implementation Checklist

### Pre-Implementation
- [ ] Team alignment on approach
- [ ] Dependencies approved
- [ ] Timeline agreed
- [ ] Success metrics defined

### Phase 1
- [ ] Dependencies updated
- [ ] Feature flag working
- [ ] LangChain components created
- [ ] All tests passing (Phase 1)
- [ ] Code reviewed and merged

### Phase 2
- [ ] Memory implementation done
- [ ] Retriever implementation done
- [ ] RAG chain implemented
- [ ] A/B testing completed
- [ ] All tests passing (Phase 2)
- [ ] Code reviewed and merged

### Phase 3
- [ ] Document processor migrated
- [ ] Multi-format support added
- [ ] Performance optimized
- [ ] All tests passing (Phase 3)
- [ ] Code reviewed and merged

### Phase 4 (Optional)
- [ ] Agents implemented
- [ ] Tools working
- [ ] Observability added
- [ ] All tests passing
- [ ] Code reviewed and merged

### Phase 5
- [ ] Staged rollout planned
- [ ] Monitoring in place
- [ ] Fallback ready
- [ ] 100% rollout completed
- [ ] Old code removed
- [ ] Documentation updated

---

## 🎯 Key Metrics to Track

### Code Metrics
| Metric | Target | Current | After |
|--------|--------|---------|-------|
| RAG Service LOC | <300 | ~350 | <200 |
| Test Coverage | >80% | ~60% | >90% |
| Type Coverage | >95% | ~85% | >95% |

### Performance Metrics
| Metric | Target | Notes |
|--------|--------|-------|
| First message latency | <3s | p95 |
| Follow-up message latency | <2s | p95 |
| Retrieval latency | <1s | p95 |
| LLM response latency | <2s | p95 |

### Quality Metrics
| Metric | Target | Notes |
|--------|--------|-------|
| Response quality | Same+ | Manual evaluation |
| Hallucination rate | <5% | Manual review |
| Source accuracy | >95% | Manual review |
| User satisfaction | Same+ | If applicable |

---

## 🚀 Go/No-Go Criteria

### Go to Phase 2
- [ ] All Phase 1 tests passing
- [ ] Code review approved
- [ ] Feature flag working correctly
- [ ] No breaking changes

### Go to Phase 3
- [ ] RAG chain working as well as old version
- [ ] A/B testing shows no regression
- [ ] Performance acceptable
- [ ] All Phase 2 tests passing

### Go to Phase 4
- [ ] Document processing quality same or better
- [ ] Multi-format support tested
- [ ] Performance optimized

### Go to Production Rollout
- [ ] All phases complete
- [ ] Fallback mechanism ready
- [ ] Monitoring dashboards set up
- [ ] Team trained on new system

---

**Status**: Ready for team review and Phase 1 kickoff
**Questions**: See LANGCHAIN_MIGRATION_GUIDE.md section "Questions for the Team"
