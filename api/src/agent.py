"""Pydantic AI agent for Warren community data."""

import os
from dataclasses import dataclass
from decimal import Decimal

import logfire
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent, Embedder, RunContext
from sqlalchemy import func, select

from .database import SessionLocal, engine
from .models import FPFPerson, FPFPost, Owner, Parcel, TaxStatus

load_dotenv()

# Configure Logfire for observability (optional - only if token is set)
if os.getenv("LOGFIRE_TOKEN"):
    logfire.configure()
    logfire.instrument_pydantic_ai()


# Pydantic models for tool outputs
class PropertySummary(BaseModel):
    """Summary of a property."""
    span: str
    address: str | None
    owner: str | None
    acres: float | None
    assessed_total: int | None
    property_type: str | None
    homestead: bool
    lat: float | None
    lng: float | None


class PropertyStats(BaseModel):
    """Aggregate statistics about properties."""
    total_parcels: int
    total_value: int
    avg_value: int
    homestead_count: int
    non_homestead_count: int
    homestead_percent: float


class PropertyTypeBreakdown(BaseModel):
    """Breakdown by property type."""
    property_type: str
    count: int
    total_value: int
    avg_value: int


class FPFPostSummary(BaseModel):
    """Summary of an FPF post for search results."""
    id: str
    title: str
    content_preview: str
    author: str | None
    town: str | None
    category: str | None
    published_at: str
    similarity_score: float


class FPFSearchResult(BaseModel):
    """Semantic search results for FPF posts."""
    query: str
    results: list[FPFPostSummary]
    total_matches: int


@dataclass
class WarrenContext:
    """Context for the Warren agent - database session."""
    pass


# Create the agent - using Pydantic AI Gateway with Claude Opus 4.5
warren_agent = Agent(
    "gateway/anthropic:claude-opus-4-5-20251101",
    system_prompt="""You are a community data assistant for Warren, Vermont. You help users
understand property data, residency patterns, community discussions, and local statistics.

Warren is a small town in the Mad River Valley with approximately 1,800 residents.
It's home to Sugarbush Resort and has a significant second-home population.
The town has about 1,800 parcels with a total assessed value of nearly $500 million.

Key insight: Only about 24% of properties have filed homestead exemptions,
indicating the majority are likely second homes or investment properties.

You also have access to Front Porch Forum (FPF) posts from the Mad River Valley community.
This includes over 58,000 posts from ~6,400 community members across Warren, Waitsfield,
Fayston, Moretown, and nearby towns. Use search_fpf_posts to find community discussions,
announcements, items for sale, and other neighborhood conversations using semantic search.

When answering questions:
- Use the tools to get precise data from the database
- Always provide specific numbers when available
- Explain what the data means in the local context
- For FPF searches, the similarity score indicates how relevant each post is to the query
- Be concise but informative
""",
    deps_type=WarrenContext,
)

# Initialize embedder for semantic search (via Gateway, large model for max quality)
fpf_embedder = Embedder("gateway/openai:text-embedding-3-large")


@warren_agent.tool
def get_property_stats(ctx: RunContext[WarrenContext]) -> PropertyStats:
    """Get aggregate statistics about all properties in Warren."""
    db = SessionLocal()
    try:
        total_parcels = db.query(func.count(Parcel.id)).scalar()
        total_value = db.query(func.sum(Parcel.assessed_total)).scalar() or 0

        homestead = db.query(func.count(TaxStatus.id)).filter(
            TaxStatus.homestead_filed == True
        ).scalar()
        non_homestead = db.query(func.count(TaxStatus.id)).filter(
            TaxStatus.homestead_filed == False
        ).scalar()

        total_with_status = homestead + non_homestead
        homestead_pct = (homestead / total_with_status * 100) if total_with_status > 0 else 0

        return PropertyStats(
            total_parcels=total_parcels,
            total_value=int(total_value),
            avg_value=int(total_value / total_parcels) if total_parcels > 0 else 0,
            homestead_count=homestead,
            non_homestead_count=non_homestead,
            homestead_percent=round(homestead_pct, 1),
        )
    finally:
        db.close()


@warren_agent.tool
def get_property_type_breakdown(ctx: RunContext[WarrenContext]) -> list[PropertyTypeBreakdown]:
    """Get breakdown of properties by type (residential, commercial, etc.)."""
    db = SessionLocal()
    try:
        results = db.query(
            Parcel.property_type,
            func.count(Parcel.id).label("count"),
            func.sum(Parcel.assessed_total).label("total_value"),
        ).group_by(Parcel.property_type).all()

        return [
            PropertyTypeBreakdown(
                property_type=r.property_type or "unknown",
                count=r.count,
                total_value=int(r.total_value or 0),
                avg_value=int(r.total_value / r.count) if r.count > 0 and r.total_value else 0,
            )
            for r in results
        ]
    finally:
        db.close()


@warren_agent.tool
def search_properties(
    ctx: RunContext[WarrenContext],
    address_contains: str | None = None,
    owner_contains: str | None = None,
    min_value: int | None = None,
    max_value: int | None = None,
    homestead_only: bool | None = None,
    property_type: str | None = None,
    limit: int = 10,
) -> list[PropertySummary]:
    """Search for properties matching criteria.

    Args:
        address_contains: Filter by address containing this text
        owner_contains: Filter by owner name containing this text
        min_value: Minimum assessed value
        max_value: Maximum assessed value
        homestead_only: If True, only show homestead properties; if False, only non-homestead
        property_type: Filter by property type (residential, commercial, etc.)
        limit: Maximum number of results to return (default 10)
    """
    db = SessionLocal()
    try:
        query = db.query(Parcel)

        if address_contains:
            query = query.filter(Parcel.address.ilike(f"%{address_contains}%"))

        if owner_contains:
            query = query.join(Owner).filter(Owner.name.ilike(f"%{owner_contains}%"))

        if min_value is not None:
            query = query.filter(Parcel.assessed_total >= min_value)

        if max_value is not None:
            query = query.filter(Parcel.assessed_total <= max_value)

        if property_type:
            query = query.filter(Parcel.property_type == property_type)

        if homestead_only is not None:
            query = query.join(TaxStatus).filter(TaxStatus.homestead_filed == homestead_only)

        parcels = query.limit(limit).all()

        results = []
        for p in parcels:
            owner_name = p.owners[0].name if p.owners else None
            tax = p.tax_status[0] if p.tax_status else None

            results.append(PropertySummary(
                span=p.span,
                address=p.address,
                owner=owner_name,
                acres=float(p.acres) if p.acres else None,
                assessed_total=p.assessed_total,
                property_type=p.property_type,
                homestead=tax.homestead_filed if tax else False,
                lat=float(p.lat) if p.lat else None,
                lng=float(p.lng) if p.lng else None,
            ))

        return results
    finally:
        db.close()


@warren_agent.tool
def get_property_by_span(ctx: RunContext[WarrenContext], span: str) -> PropertySummary | None:
    """Get detailed information about a specific property by its SPAN ID."""
    db = SessionLocal()
    try:
        parcel = db.query(Parcel).filter(Parcel.span == span).first()
        if not parcel:
            return None

        owner_name = parcel.owners[0].name if parcel.owners else None
        tax = parcel.tax_status[0] if parcel.tax_status else None

        return PropertySummary(
            span=parcel.span,
            address=parcel.address,
            owner=owner_name,
            acres=float(parcel.acres) if parcel.acres else None,
            assessed_total=parcel.assessed_total,
            property_type=parcel.property_type,
            homestead=tax.homestead_filed if tax else False,
            lat=float(parcel.lat) if parcel.lat else None,
            lng=float(parcel.lng) if parcel.lng else None,
        )
    finally:
        db.close()


@warren_agent.tool
async def search_fpf_posts(
    ctx: RunContext[WarrenContext],
    query: str,
    limit: int = 10,
    category: str | None = None,
    town: str | None = None,
) -> FPFSearchResult:
    """Search Front Porch Forum posts using semantic similarity.

    Args:
        query: Natural language search query (e.g., "lost dog", "road construction", "firewood for sale")
        limit: Maximum number of results (default 10, max 50)
        category: Filter by category (e.g., "Announcements", "For sale", "Free items", "Seeking items")
        town: Filter by author's town (e.g., "Warren", "Waitsfield", "Fayston", "Moretown")
    """
    from sqlalchemy.orm import Session

    # Clamp limit
    limit = min(max(1, limit), 50)

    # Generate query embedding
    result = await fpf_embedder.embed_query(query)
    query_embedding = result.embeddings[0]

    with Session(engine) as db:
        # Check if we have any embeddings
        embedded_count = db.scalar(
            select(func.count(FPFPost.id)).where(FPFPost.embedding.isnot(None))
        )

        if embedded_count == 0:
            return FPFSearchResult(
                query=query,
                results=[],
                total_matches=0,
            )

        # Build query with cosine similarity
        # pgvector cosine_distance returns 0 for identical, 2 for opposite
        # Convert to similarity: 1 - (distance / 2) gives us 0-1 range
        similarity = 1 - (FPFPost.embedding.cosine_distance(query_embedding) / 2)

        stmt = (
            select(
                FPFPost,
                FPFPerson.name.label("author_name"),
                FPFPerson.town.label("author_town"),
                similarity.label("similarity"),
            )
            .join(FPFPerson, FPFPost.person_id == FPFPerson.id)
            .where(FPFPost.embedding.isnot(None))
            .order_by(similarity.desc())
        )

        if category:
            stmt = stmt.where(FPFPost.category == category)
        if town:
            stmt = stmt.where(FPFPerson.town == town)

        stmt = stmt.limit(limit)

        rows = db.execute(stmt).all()

        results = []
        for row in rows:
            post = row.FPFPost
            content_preview = post.content[:200] if post.content else ""
            if len(post.content) > 200:
                content_preview += "..."

            results.append(
                FPFPostSummary(
                    id=str(post.id),
                    title=post.title,
                    content_preview=content_preview,
                    author=row.author_name,
                    town=row.author_town,
                    category=post.category,
                    published_at=post.published_at.isoformat(),
                    similarity_score=round(float(row.similarity), 4),
                )
            )

        return FPFSearchResult(
            query=query,
            results=results,
            total_matches=len(results),
        )


async def chat(message: str) -> str:
    """Send a message to the Warren agent and get a response."""
    result = await warren_agent.run(message, deps=WarrenContext())
    return result.output


# For testing
if __name__ == "__main__":
    import asyncio

    async def main():
        # Test queries
        queries = [
            "How many properties are in Warren?",
            "What percentage of properties are primary residences vs second homes?",
            "Show me properties on Woods Road",
        ]

        for q in queries:
            print(f"\n{'='*60}")
            print(f"Q: {q}")
            print(f"{'='*60}")
            response = await chat(q)
            print(f"A: {response}")

    asyncio.run(main())
