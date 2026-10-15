"""
RAG without a vector database.

Retrieval: SQLite FTS5 (keyword / full-text search, built into Python's stdlib).
Generation: any OpenAI-compatible chat endpoint.

Usage:
    python rag_fts5.py "release features in 2025"
"""

import argparse
import os
import sqlite3
import sys
from pathlib import Path

DOCS_DIR = Path(__file__).parent / "docs"
TOP_K = 5


# ---------- 1. Build the FTS5 index ----------

def chunk_file(path: Path):
    """Split a markdown file into chunks. Paragraph-level is fine here."""
    text = path.read_text(encoding="utf-8")
    # Split on blank lines, drop empties, keep chunks reasonably sized.
    chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
    return [(path.name, c) for c in chunks]


def build_index() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE VIRTUAL TABLE chunks USING fts5("
        "  source,   "      # filename
        "  content,  "      # chunk text
        "  tokenize = 'porter unicode61'"
        ")"
    )

    rows = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        rows.extend(chunk_file(path))

    conn.executemany("INSERT INTO chunks (source, content) VALUES (?, ?)", rows)
    conn.commit()
    print(f"[index] {len(rows)} chunks from {len(list(DOCS_DIR.glob('*.md')))} files", file=sys.stderr)
    return conn


# ---------- 2. Retrieve ----------

def retrieve(conn: sqlite3.Connection, query: str, k: int = TOP_K):
    """
    FTS5 MATCH query. `rank` is FTS5's built-in relevance score (lower = better).
    We pass the raw user query — FTS5 handles the tokenization.
    """
    sql = """
        SELECT source, content, rank
        FROM chunks
        WHERE chunks MATCH ?
        ORDER BY rank
        LIMIT ?
    """
    try:
        rows = conn.execute(sql, (query, k)).fetchall()
    except sqlite3.OperationalError as e:
        # FTS5 is picky about syntax (bare `AND`, `*`, etc.). Fall back to OR.
        safe = " OR ".join(t for t in query.split() if t.isalnum())
        rows = conn.execute(sql, (safe, k)).fetchall()
    return rows


# ---------- 3. Generate ----------

def generate(query: str, chunks):
    """Call an OpenAI-compatible endpoint. Keep it boring and replaceable."""
    from openai import OpenAI  # imported lazily so --no-llm needs no install

    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ.get("OPENAI_BASE_URL"),  # optional
    )

    context = "\n\n".join(f"[{src}]\n{txt}" for src, txt, _ in chunks)
    prompt = (
        "Answer the question using ONLY the context below. "
        "If the context doesn't contain the answer, say so.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {query}"
    )

    resp = client.chat.completions.create(
        model=os.environ.get("MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return resp.choices[0].message.content


# ---------- 4. CLI ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--no-llm", action="store_true", help="print retrieved chunks only")
    ap.add_argument("-k", type=int, default=TOP_K)
    args = ap.parse_args()

    conn = build_index()
    chunks = retrieve(conn, args.query, args.k)

    print(f"\n=== retrieved {len(chunks)} chunks ===")
    for src, txt, rank in chunks:
        preview = txt.replace("\n", " ")[:120]
        print(f"  [{rank:+.3f}] {src}: {preview}...")

    if args.no_llm:
        return
    if not chunks:
        print("\n(no chunks retrieved — nothing to generate from)", file=sys.stderr)
        return

    print("\n=== answer ===")
    print(generate(args.query, chunks))


if __name__ == "__main__":
    main()
