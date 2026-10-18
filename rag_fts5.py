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
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
DB_PATH = BASE_DIR / "rag_fts5.sqlite"
TOP_K = 5

# ---------- 1. Build the FTS5 index ----------

def chunk_file(path: Path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    chunks = []
    current = []

    for line in lines:
        if line.startswith("#"):
            if current:
                chunks.append("\n".join(current).strip())
                current = []
            current.append(line)
        else:
            current.append(line)

    if current:
        chunks.append("\n".join(current).strip())

    return [(path.name, c) for c in chunks if c]

def iter_source_files():
    return sorted(
        path for path in DOCS_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".txt"}
    )


def build_index() -> sqlite3.Connection:
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "CREATE VIRTUAL TABLE chunks USING fts5("
        "  source,   "      # filename
        "  content,  "      # chunk text
        "  tokenize = 'porter unicode61'"
        ")"
    )

    rows = []
    source_files = iter_source_files()
    for path in source_files:
        rows.extend(chunk_file(path))

    conn.executemany("INSERT INTO chunks (source, content) VALUES (?, ?)", rows)
    conn.commit()
    print(f"[index] {len(rows)} chunks from {len(source_files)} files", file=sys.stderr)
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
    except sqlite3.OperationalError:
        # FTS5 is picky about syntax (bare `AND`, `*`, etc.). Fall back to OR.
        safe = " OR ".join(t for t in query.split() if t.isalnum())
        rows = conn.execute(sql, (safe, k)).fetchall()
    return rows


# ---------- 3. Generate ----------

def generate(query: str, chunks):
    """Call the Gemini Interactions API using the local docs as grounding context."""
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "Gemini support requires the 'google-genai' package. Install it with: pip install google-genai"
        ) from exc

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Set it before running the LLM mode.")

    client = genai.Client(api_key=api_key)

    context = "\n\n".join(f"[{src}]\n{txt}" for src, txt, _ in chunks)
    prompt = (
        "Answer the question using ONLY the context below. "
        "If the context doesn't contain the answer, say so.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {query}"
    )

    interaction = client.interactions.create(
        model=os.environ.get("MODEL", "gemini-3.8-flash"),
        input=prompt,
    )

    if not hasattr(interaction, "output_text"):
        raise RuntimeError("Gemini interaction did not return output_text.")

    return interaction.output_text


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
        preview = txt.replace("\n", " ")
        print(f"  [{rank:+.3f}] {src}: {preview}...")

    if args.no_llm:
        return
    if not chunks:
        print("\n(no chunks retrieved — nothing to generate from)", file=sys.stderr)
        return

    print("\n=== answer ===")
    try:
        print(generate(args.query, chunks))
    except Exception as exc:
        print(f"\n[llm error] {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
