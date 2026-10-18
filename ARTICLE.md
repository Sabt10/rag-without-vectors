Here's the rewritten `ARTICLE.md`. Your sentences and voice are kept throughout — I've restructured around the experiments and connected the argument to the evidence. The terminal output is quoted sparingly, as evidence, not pasted wholesale.

---

# A vector DB is not RAG

One day, while commuting, my friend told me about a problem at work. He had been asked to build a RAG pipeline, but he didn't have access to the vector DB. He assumed this made it impossible.

I said that in order to build a RAG, it's not always necessary to have a vector DB. A vector DB could be used, for example, for semantic searching, where intent could be diluted.

He said that's why we build RAG — for semantic searching, and that's where the vector DB is used.

There is a common misconception that we have to always use a vector DB, or that it equates to a RAG pipeline. But RAG is all about retrieving the context of a specific data based on the query rather than the entire data set.

What data it is, or the techniques used to extract it, is just implementation. A RAG pipeline could also be just a keyword query run, and the data retrieved. SQLite FTS5 is a good example — it's full-text search built into a single file, no server, no embeddings, and it can sit behind a RAG pipeline just fine. The same goes for Postgres full-text search using `tsvector`, or BM25 in Elasticsearch, or even a plain SQL query with a `WHERE` clause on structured metadata.

It all depends on the use case. How the data is extracted is based upon the intent and the scope. A vector DB is one of the implementation techniques — one apt data extraction technique — rather than RAG itself.

---

## So I built it

Arguments are cheap. I wanted to know whether a keyword-only RAG pipeline actually works, and where it breaks. So I built one: a small corpus of release notes and ops docs, indexed with SQLite FTS5, retrieved by keyword match, and passed to Gemini for generation. No vectors, no embeddings, no vector database.

The code is in this repo. What follows is what I found when I ran it.

---

## Experiment 1: lexical matching is literal

The first thing I tried was asking a natural-language question:

```
$ python rag_fts5.py "what is the new features in 2025 q3"
[index] 58 chunks from 9 files
=== retrieved 0 chunks ===
(no chunks retrieved — nothing to generate from)
```

Zero chunks. The pipeline refused to generate, because there was nothing to ground the answer in.

Then I tried a keyword-shaped query against the same index:

```
$ python rag_fts5.py "Q3 2025"
[index] 58 chunks from 9 files
=== retrieved 5 chunks ===
  [-3.964] release-notes-2025-q3.md: # Release Notes: Q3 2025...
  [-3.432] release-notes-2025-q3.md: ## Outcome...
  [-3.354] release-notes-2025-q3.md: ## Feature updates...
  ...
```

Five chunks, all from the right document.

This is not a bug in the demo. It is the expected behavior of a lexical FTS setup. FTS5 matches tokens — it doesn't "understand" that "what is the new features in 2025 q3" means "give me the Q3 2025 release notes." The stopwords and phrasing dilute the match. A keyword query works because it's shaped like the thing being searched for.

That's the boundary of a plain keyword retriever, and it's worth naming honestly. It's also the exact failure that a vector DB is usually brought in to fix — which is why the next two experiments matter.

---

## Experiment 2: chunking determines retrieval quality

The first version of the chunker split documents on blank lines. That produced 58 chunks from 9 files — but for a targeted query like `"Q3 2025 security patches"`, it collapsed the entire release note into one giant block:

```
=== retrieved 1 chunks ===
  [-4.415] release-notes-2025-q3.md: We shipped several security patches
  for authentication tokens, audit logging, and service-to-service
  communication. The ...
```

One chunk. The right document, but a blob that mixes several unrelated sections together.

I switched to heading-based chunking — split on `##` headings instead of blank lines. Same corpus, same retriever, same FTS5 index. The chunk count dropped to 29, and the retrieval got sharper:

```
$ python rag_fts5.py "Q3 2025 security patches"
[index] 29 chunks from 9 files
=== retrieved 1 chunks ===
  [-5.104] release-notes-2025-q3.md: # Release Notes: Q3 2025
  ## Customer-facing improvements ...
```

The better chunk was retrieved. The better chunk meant better context for the LLM, which is the ultimate goal of RAG. No retriever change was needed to get there — the lever was chunking.

This is the point that gets lost when people reach for a vector DB first. The retriever is one variable. Chunking is another, and it often matters more.

---

## Experiment 3: grounding is only as good as retrieval

The `"Q3 2025"` query from Experiment 1 retrieved five chunks — but they were all headings and short section titles. The LLM's answer reflected that:

```
Based on the context, "Q3 2025" refers to the Release Notes: Q3 2025,
which lists the following sections:
* Outcome
* Feature updates
* Customer-facing improvements
* Security and reliability
(Note: If you are looking for specific details beyond these headings,
the context does not contain that information.)
```

The model wasn't hallucinating. It was faithfully summarizing the five chunks it received. The chunks happened to be headings, so the answer was a list of headings. Garbage chunks in, plausible-but-shallow answer out.

Here's the part worth sitting with: **a vector DB would not have fixed this.** The chunks were headings. Semantic search can't retrieve detail that isn't in the chunk. The fix was the same one from Experiment 2 — better chunking — not a different retriever.

That's why the "vectors solve hallucination" argument doesn't hold up. Retrieval quality is a function of chunking, corpus shape, and query shape, all of which are orthogonal to the retriever. Vectors are excellent at one specific thing — matching meaning across different words — and they're genuinely the right tool when that's what you need. But they don't fix a bad chunk, and they don't fix a query that doesn't match the corpus.

---

## The fix that actually works: let the LLM rewrite the query

Experiment 1's failure — a natural-language question returning zero chunks — has a clean fix, and it isn't a vector DB. It's query rewriting.

If the LLM reads `"what is the new features in 2025 q3"` and emits `"Q3 2025 new features"`, the FTS5 index will find the right chunks. The LLM does the understanding; the retriever just needs a clean query.

That's what `rag_chat.py` in this repo demonstrates — a multi-turn chatbot where the LLM compiles each follow-up into a searchable query before it hits FTS5. Same index, same keyword retrieval, no vectors. The LLM is the query compiler.

This is the part the "RAG needs vectors" framing misses entirely. Semantic search is one way to handle intent mismatch. Query rewriting is another, and it's often simpler, cheaper, and more debuggable — because you can read the rewritten query and see what the retriever actually searched for.

---

## Where vectors still win

None of this is an argument that vectors are useless. Semantic search genuinely earns its keep when:

- The corpus is paraphrase-heavy and the query vocabulary doesn't overlap with the document vocabulary
- You need cross-lingual retrieval
- The user asks fuzzy conceptual questions with no clean keyword shape
- You have millions of documents and need approximate nearest-neighbor speed

For a small structured corpus with clear section headings, FTS5 or `tsvector` or BM25 will often match or beat a vector index on the queries that matter — and you can debug them by reading the query.

The point isn't that vectors are bad. The point is that they're one technique, and the field has been treating them as the definition.

---

## Closing

A vector DB is one of the implementation techniques — one apt data extraction technique — rather than RAG itself. RAG is retrieve, augment, generate. The retriever is a choice. Chunking is a choice. Query rewriting is a choice. Getting those choices right matters more than which index you pick.

The repo is here: (https://github.com/Sabt10/rag-without-vectors.git). It runs on SQLite FTS5 and a Gemini key. No vectors, no embeddings, no framework. Just retrieve, augment, generate.

