One day, while commuting, my friend told me about a problem at work. He had been asked to build a RAG pipeline, but he didn't have access to the vector DB. He assumed this made it impossible.

I said that in order to build a RAG, it's not always necessary to have a vector DB. A vector DB could be used, for example, for semantic searching, where intent could be diluted.

He said that's why we build RAG - for semantic searching, and that's where the vector DB is used.

There is a common misconception that we have to always use a vector DB, or that it equates to a RAG pipeline. But RAG is all about retrieving the context of a specific data based on the query rather than the entire data set.

What data it is, or the techniques used to extract it, is just implementation. A RAG pipeline could also be just a keyword query run, and the data retrieved. SQLite FTS5 is a good example, it's full-text search built into a single file, no server, no embeddings, and it can sit behind a RAG pipeline just fine. The same goes for Postgres full-text search using tsvector, or BM25 in Elasticsearch, or even a plain SQL query with a WHERE clause on structured metadata.

It all depends on the use case. How the data is extracted is based upon the intent and the scope. A vector DB is one of the implementation techniques - one apt data extraction technique, rather than RAG itself.
