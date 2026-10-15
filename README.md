# RAG without vectors

> A vector DB is not RAG.

Most people assume it is. You're asked to build a RAG pipeline, you're
told to reach for a vector database, and the implementation detail quietly
became the definition. It isn't. RAG is retrieve, augment, generate : the
retriever is a choice.

This repository is a working pipeline on SQLite FTS5. No vectors, no embeddings,
no framework.

## Run it
...

## What's in here
...

## Why

Full write-up: [link to your article]

## What this is not

Not a benchmark of FTS5 vs. vector search. Vector search is genuinely better
for some queries. This is a demonstration that RAG is a pattern, and the
retriever is a choice.
