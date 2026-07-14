# ADR 0063: Retrieval Providers Are Isolated Behind Ports

Status: Accepted

EmbeddingProvider and RetrievalIndex are framework-independent domain ports. SDK, PostgreSQL, and pgvector behavior belongs in infrastructure adapters so providers can change without changing Academic, Retrieval application, or Teaching contracts.
