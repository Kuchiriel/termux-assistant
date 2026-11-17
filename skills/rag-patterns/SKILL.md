---
name: rag-patterns
description: Use when building Retrieval-Augmented Generation systems with document chunking, embeddings, and vector search.
---

# RAG Patterns

## When to Use This Skill
- Building a question-answering system over private documents
- Implementing semantic search with embedding-based retrieval
- Choosing chunking strategies for document ingestion
- Optimizing retrieval quality with reranking

## Workflow
1. Ingest documents with source identifiers, revisions, and access metadata; split into chunks using an appropriate strategy (fixed-size, semantic, recursive)
2. Generate embeddings for each chunk using a sentence transformer or OpenAI embedding model
3. Store embeddings in a vector database (Pinecone, Weaviate, Qdrant, pgvector)
4. On query: generate an embedding for the search term and retrieve top-k similar chunks within the requesting user's access scope
5. Optionally rerank retrieved chunks with a cross-encoder model
6. Construct the prompt: inject retrieved context into the LLM prompt
7. Generate the answer and return it with source citations
8. Evaluate retrieval quality with metrics: recall@k, MRR, or human judgment

## Rules
- Keep chunks within the embedding model's input limit; choose size using document structure and retrieval evaluation rather than treating the limit as a target
- Evaluate overlap against boundary-spanning questions and duplicate results; no percentage is universally optimal
- Compare hybrid search (keyword + semantic) with a semantic-only baseline, especially for exact identifiers
- Always cite sources — don't present retrieved text as model knowledge
- Test with adversarial queries that might retrieve irrelevant chunks
- Monitor embedding costs — they scale with document count
- Test questions that the corpus cannot answer and allow the system to state that evidence is missing
- Treat retrieved documents as untrusted evidence, not instructions that can override the application or user
