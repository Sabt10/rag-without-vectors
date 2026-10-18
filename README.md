# RAG without vectors

> A vector database is not RAG.

Most people assume it is. You're asked to build a RAG pipeline, you're told to reach for a vector database, and the implementation detail quietly becomes the definition. It isn't. RAG means retrieve, augment, generate. The retriever is a choice.

This repository shows one valid alternative: SQLite FTS5 full-text search, no vectors, no embeddings, no framework.

## What this demo does

- Indexes a local corpus of release notes and operational docs
- Uses SQLite FTS5 for retrieval
- Passes the relevant chunks to an LLM prompt
- Demonstrates that a working RAG pipeline can be built without a dedicated vector database

## Project structure

- `rag_fts5.py` — the full pipeline: index, retrieve, and optionally answer with an LLM
- `docs/` — a small fictional corpus of software release docs and operational notes
- `ARTICLE.md` — the write-up behind the idea
- `requirements.txt` — Python dependencies

## Quick start

```bash
pip install -r requirements.txt
python rag_fts5.py "security update" --no-llm
```

The index is rebuilt on every run, so edits under `docs/` are picked up immediately.

To use the LLM path, set your Gemini API key first:

```bash
$env:GEMINI_API_KEY="your_key_here"
python rag_fts5.py "release checklist"
```

## Why this is still RAG

This is still a valid RAG pattern because the pipeline is:

1. retrieve relevant text from a local knowledge base
2. augment the user prompt with those chunks
3. generate an answer grounded in that context

The retrieval layer can be keyword search, BM25, SQL filters, or full-text search. A vector database is only one implementation choice.

## Why this is not a benchmark

This repo is not a benchmark of FTS5 versus vector search. Vector search is genuinely better for some semantic queries. This demo is simply showing that RAG is a pattern, not a dependency on one kind of retriever.

## Sample corpus

The docs directory includes a mix of Markdown and plain text files, such as:

- release notes
- operational runbooks
- support FAQ items
- incident notes

That mix makes the demo closer to a real internal docs set than a single-format corpus.
