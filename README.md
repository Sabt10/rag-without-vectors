# rag-without-vectors
A vector DB is not RAG.  Most people assume it is. To build a RAG pipeline, you're told to reach for a vector database, and somewhere along the way the implementation detail became the definition. It isn't. RAG is retrieve, augment, generate ,the retriever is a choice. Here's a working pipeline on SQLite FTS5. 
