"""Generate embeddings for FPF posts using Pydantic AI Embedder."""

import argparse
import asyncio
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic_ai import Embedder
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database import engine, init_db
from src.models import FPFPost

load_dotenv()

# Configuration - use Gateway for OpenAI embeddings (large model for max quality)
EMBEDDING_MODEL = "gateway/openai:text-embedding-3-large"
BATCH_SIZE = 100  # Process 100 posts at a time
COMMIT_EVERY = 500  # Commit after this many posts


def get_text_for_embedding(post: FPFPost) -> str:
    """Combine title and content for embedding."""
    parts = []
    if post.title:
        parts.append(post.title)
    if post.content:
        parts.append(post.content)
    if post.category:
        parts.append(f"Category: {post.category}")
    return "\n".join(parts)


async def embed_batch(
    embedder: Embedder,
    posts: list[FPFPost],
) -> int:
    """Embed a batch of posts. Returns count of successful embeddings."""
    texts = [get_text_for_embedding(p) for p in posts]

    try:
        result = await embedder.embed_documents(texts)

        for i, post in enumerate(posts):
            post.embedding = result.embeddings[i]
            post.embedding_model = EMBEDDING_MODEL
            post.embedded_at = datetime.utcnow()

        return len(posts)
    except Exception as e:
        print(f"  Error embedding batch: {e}")
        return 0


async def main(force_reembed: bool = False, limit: int | None = None):
    """Main embedding pipeline."""
    print(f"Initializing embedder with model: {EMBEDDING_MODEL}")
    embedder = Embedder(EMBEDDING_MODEL)

    # Ensure tables exist
    init_db()

    with Session(engine) as session:
        # Count total posts
        total_posts = session.scalar(select(func.count(FPFPost.id)))
        already_embedded = session.scalar(
            select(func.count(FPFPost.id)).where(FPFPost.embedding.isnot(None))
        )

        print(f"Total posts in database: {total_posts}")
        print(f"Already embedded: {already_embedded}")

        # Build query for posts needing embeddings
        query = select(FPFPost)

        if not force_reembed:
            query = query.where(FPFPost.embedding.is_(None))

        if limit:
            query = query.limit(limit)

        posts = list(session.scalars(query))
        to_embed = len(posts)

        if to_embed == 0:
            print("No posts need embedding.")
            return

        print(f"Posts to embed: {to_embed}")
        if limit:
            print(f"  (limited to {limit})")
        print()

        embedded = 0
        errors = 0

        for i in range(0, to_embed, BATCH_SIZE):
            batch = posts[i : i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (to_embed + BATCH_SIZE - 1) // BATCH_SIZE

            print(f"[Batch {batch_num}/{total_batches}] Embedding {len(batch)} posts...", end=" ")

            count = await embed_batch(embedder, batch)
            embedded += count

            if count < len(batch):
                errors += len(batch) - count

            print(f"done ({embedded}/{to_embed})")

            # Commit periodically
            if embedded % COMMIT_EVERY == 0 or i + BATCH_SIZE >= to_embed:
                session.commit()
                print(f"  Committed to database")

        print()
        print("=" * 50)
        print(f"Embedding complete!")
        print(f"  Successfully embedded: {embedded}")
        if errors:
            print(f"  Errors: {errors}")
        print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate embeddings for FPF posts using OpenAI text-embedding-3-small"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-embed posts that already have embeddings",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of posts to embed (useful for testing)",
    )

    args = parser.parse_args()

    print("=" * 50)
    print("FPF Post Embedding Pipeline")
    print("=" * 50)
    print()

    asyncio.run(main(force_reembed=args.force, limit=args.limit))
