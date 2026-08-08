"""Initialize the SQLite database (schema + seed) and build the RAG index."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import db, rag_engine  # noqa: E402


def main():
    db.init_db()
    print("Database initialized at data/app.db")
    n = rag_engine.build_index()
    print(f"RAG index built: {n} chunks from data/docs/")


if __name__ == "__main__":
    main()
