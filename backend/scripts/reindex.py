"""
Build the semantic search index from the database.

Usage:
  python scripts/reindex.py          # index conversations/documents missing from the index
  python scripts/reindex.py --all    # rebuild every completed conversation
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.ai.rag.indexer import index_conversation, index_missing_conversations, index_missing_knowledge
from app.core.config import settings
from app.db.models import Conversation


async def reindex(rebuild_all: bool = False) -> None:
    engine = create_engine(settings.database_sync_url)
    db = sessionmaker(bind=engine)()
    try:
        if rebuild_all:
            ids = db.execute(select(Conversation.id).where(Conversation.status == "completed")).scalars().all()
            for conv_id in ids:
                await index_conversation(db, conv_id)
            conversations = len(ids)
        else:
            conversations = await index_missing_conversations(db)
        documents = await index_missing_knowledge(db)
        print(f"Indexed {conversations} conversation(s) and {documents} knowledge document(s) "
              f"using {settings.embedding_provider} embeddings.")
    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--all", action="store_true", help="rebuild every completed conversation")
    asyncio.run(reindex(parser.parse_args().all))
