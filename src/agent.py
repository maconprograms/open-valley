"""Pydantic AI agent for Warren community data."""

import os
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

import logfire
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_ai import Agent, Embedder, RunContext
from sqlalchemy import func, select

from .database import SessionLocal, engine
from .models import (
    Dwelling,
    FPFPerson,
    FPFPost,
    Organization,
    Parcel,
    Person,
    PropertyOwnership,
    STRListing,
    TaxStatus,
)

load_dotenv()

# Configure Logfire for observability (optional - only if token is set)
if os.getenv("LOGFIRE_TOKEN"):
    logfire.configure()
    logfire.instrument_pydantic_ai()


# ============================================================================
# Schema Engineering: Intelligence in Type Hints
# The Field descriptions and validators ARE the prompts - not prose instructions
# ============================================================================


class MailingAddressAnalysis(BaseModel):
    """Parsed mailing address with residency indicators.

    Uses field validators to auto-extract state from raw address string,
    enabling automatic detection of out-of-state property owners.
    """

    raw_address: str = Field(description="The complete mailing address as stored")
    state: str | None = Field(
        default=None,
        description="Two-letter state code extracted from address (e.g., VT, FL, NY)"
    )
    is_vermont: bool = Field(
        default=False,
        description="True if mailing address is in Vermont"
    )
    is_out_of_state: bool = Field(
        default=False,
        description="True if mailing address is NOT in Vermont (potential second home indicator)"
    )

    @model_validator(mode='after')
    def parse_and_analyze_address(self) -> 'MailingAddressAnalysis':
        """Extract state from address and compute residency flags."""
        if not self.raw_address:
            return self

        addr_upper = self.raw_address.upper().strip()

        # Pattern 1: "City, ST 12345" or "City, ST 12345-6789"
        match = re.search(r',\s*([A-Z]{2})\s*\d{5}(?:-\d{4})?', addr_upper)
        if match:
            self.state = match.group(1)
        else:
            # Pattern 2: State name spelled out followed by zip
            state_map = {
                'VERMONT': 'VT', 'FLORIDA': 'FL', 'NEW YORK': 'NY',
                'CONNECTICUT': 'CT', 'MASSACHUSETTS': 'MA', 'NEW JERSEY': 'NJ',
                'NEW HAMPSHIRE': 'NH', 'CALIFORNIA': 'CA', 'TEXAS': 'TX',
                'RHODE ISLAND': 'RI', 'PENNSYLVANIA': 'PA', 'MAINE': 'ME',
            }
            for state_name, abbrev in state_map.items():
                if state_name in addr_upper:
                    self.state = abbrev
                    break

        # Compute residency flags
        if self.state:
            self.is_vermont = self.state == 'VT'
            self.is_out_of_state = self.state != 'VT'

        return self


class PropertySummary(BaseModel):
    """Summary of a property with mailing address intelligence.

    The mailing address fields enable detection of potential second homes:
    - If homestead_filed=True but is_out_of_state=True → suspicious
    - If mailing_state is FL, NY, CT, MA → likely second home
    """

    span: str
    address: str | None
    owner: str | None
    acres: float | None
    assessed_total: int | None
    property_type: str | None
    homestead: bool
    lat: float | None
    lng: float | None

    # NEW: Mailing address intelligence (Phase 1 of Schema Engineering)
    mailing_address: str | None = Field(
        default=None,
        description="Owner's mailing address (may differ from property address)"
    )
    mailing_state: str | None = Field(
        default=None,
        description="Two-letter state code parsed from mailing address"
    )
    is_out_of_state: bool = Field(
        default=False,
        description="True if mailing address is NOT in Vermont - key second home indicator"
    )


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


class PropertyCategory(BaseModel):
    """A category in the property breakdown aligned with Vermont H.454."""
    name: str = Field(description="Category name (e.g., 'Primary Residences', 'Second Homes')")
    count: int = Field(description="Number of parcels in this category")
    value: int = Field(description="Total assessed value")
    avg_value: int = Field(description="Average assessed value per parcel")
    color: str = Field(description="Hex color for visualization")
    description: str = Field(description="Brief description of what this category includes")


class PropertyBreakdownResult(BaseModel):
    """Complete breakdown of Warren properties by residency/use category.

    Aligned with Vermont Act 73 of 2025 proposed property classifications:
    - Homestead (Primary Residence)
    - Non-homestead Residential (Second Homes)
    - Non-homestead Apartment (Rentals)
    - Non-homestead Non-Residential (Commercial, Land)
    """
    categories: list[PropertyCategory]
    total_parcels: int
    total_value: int
    headline: str = Field(description="Main headline summarizing the key insight")
    subheadline: str = Field(description="Supporting detail with total counts and values")


class DwellingSummary(BaseModel):
    """Summary of a dwelling unit for display and map visualization.

    A dwelling is a single habitable unit within a parcel - a parcel may contain
    multiple dwellings (e.g., duplex, ADU, or multiple STR units).
    """
    id: str
    address: str | None
    unit_number: str | None = Field(
        default=None,
        description="Unit identifier if multiple dwellings on parcel"
    )
    bedrooms: int | None
    tax_classification: str | None = Field(
        description="HOMESTEAD, NHS_RESIDENTIAL, or NHS_NONRESIDENTIAL per Act 73"
    )
    use_type: str | None = Field(
        description="Specific use: owner_occupied_primary, owner_occupied_secondary, short_term_rental, etc."
    )
    is_str: bool = Field(
        default=False,
        description="True if this dwelling is used as a short-term rental"
    )
    str_name: str | None = Field(
        default=None,
        description="STR listing name if is_str=True"
    )
    str_price_per_night: int | None = Field(
        default=None,
        description="STR nightly rate in cents"
    )
    lat: float | None
    lng: float | None


class DwellingBreakdownResult(BaseModel):
    """Breakdown of all Warren dwellings by Act 73 classification.

    Key insight: Dwellings != Parcels. A single parcel can have multiple
    dwelling units, each classified independently.
    """
    total_dwellings: int
    homestead_count: int = Field(description="HOMESTEAD - owner's primary residence")
    nhs_residential_count: int = Field(description="NHS_RESIDENTIAL - second homes, STRs")
    nhs_nonresidential_count: int = Field(description="NHS_NONRESIDENTIAL - commercial, LTR, seasonal")
    str_count: int = Field(description="Dwellings used as short-term rentals")
    headline: str
    use_type_breakdown: dict[str, int] = Field(
        description="Count by specific use type"
    )


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
def get_property_breakdown(ctx: RunContext[WarrenContext]) -> PropertyBreakdownResult:
    """Get a breakdown of all Warren properties by residency/use category.

    Aligned with Vermont Act 73 of 2025 proposed classifications:
    - Primary Residences (Homestead filed)
    - Second Homes / Vacation Properties
    - Rental Properties (Multi-family without homestead)
    - Commercial / Land (Non-residential)

    This is the key visualization for understanding Warren's property composition
    and its relevance to Vermont's second-home tax debate.
    """
    db = SessionLocal()
    try:
        # 1. Primary Residences (Homestead filed - any property type)
        hs_result = db.query(
            func.count(Parcel.id),
            func.sum(Parcel.assessed_total)
        ).join(TaxStatus).filter(TaxStatus.homestead_filed == True).first()
        hs_count, hs_value = hs_result[0] or 0, hs_result[1] or 0

        # 2. Second Homes (residential + other without homestead)
        second_result = db.query(
            func.count(Parcel.id),
            func.sum(Parcel.assessed_total)
        ).join(TaxStatus).filter(
            TaxStatus.homestead_filed == False,
            Parcel.property_type.in_(['residential', 'other'])
        ).first()
        second_count, second_value = second_result[0] or 0, second_result[1] or 0

        # 3. Rental Properties (multi-family without homestead)
        rental_result = db.query(
            func.count(Parcel.id),
            func.sum(Parcel.assessed_total)
        ).join(TaxStatus).filter(
            TaxStatus.homestead_filed == False,
            Parcel.property_type == 'multi-family'
        ).first()
        rental_count, rental_value = rental_result[0] or 0, rental_result[1] or 0

        # 4. Commercial / Land
        comm_result = db.query(
            func.count(Parcel.id),
            func.sum(Parcel.assessed_total)
        ).filter(
            Parcel.property_type.in_(['commercial', 'land'])
        ).first()
        comm_count, comm_value = comm_result[0] or 0, comm_result[1] or 0

        total_count = hs_count + second_count + rental_count + comm_count
        total_value = hs_value + second_value + rental_value + comm_value

        # Calculate percentages for headline
        second_home_pct = (second_count / total_count * 100) if total_count > 0 else 0
        primary_pct = (hs_count / total_count * 100) if total_count > 0 else 0

        categories = [
            PropertyCategory(
                name="Primary Residences",
                count=hs_count,
                value=int(hs_value),
                avg_value=int(hs_value / hs_count) if hs_count > 0 else 0,
                color="#22c55e",  # green
                description="Properties with homestead exemption filed (year-round residents)"
            ),
            PropertyCategory(
                name="Second Homes / Vacation",
                count=second_count,
                value=int(second_value),
                avg_value=int(second_value / second_count) if second_count > 0 else 0,
                color="#f97316",  # orange
                description="Residential properties without homestead (includes Sugarbush condos)"
            ),
            PropertyCategory(
                name="Rental Properties",
                count=rental_count,
                value=int(rental_value),
                avg_value=int(rental_value / rental_count) if rental_count > 0 else 0,
                color="#8b5cf6",  # purple
                description="Multi-family properties without homestead (potential long-term rentals)"
            ),
            PropertyCategory(
                name="Commercial / Land",
                count=comm_count,
                value=int(comm_value),
                avg_value=int(comm_value / comm_count) if comm_count > 0 else 0,
                color="#64748b",  # slate
                description="Commercial properties and undeveloped land"
            ),
        ]

        return PropertyBreakdownResult(
            categories=categories,
            total_parcels=total_count,
            total_value=int(total_value),
            headline=f"Warren: {second_home_pct:.0f}% Second Homes, Only {primary_pct:.0f}% Primary Residences",
            subheadline=f"{total_count:,} parcels | ${total_value/1e6:.0f}M total assessed value"
        )
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
            # Search through PropertyOwnership → Person/Organization
            # as_listed_name contains the raw Grand List name
            query = query.join(PropertyOwnership).filter(
                PropertyOwnership.as_listed_name.ilike(f"%{owner_contains}%")
            )

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
            # Get primary owner from PropertyOwnership
            ownership = p.property_ownerships[0] if p.property_ownerships else None
            owner_name = ownership.as_listed_name if ownership else None
            tax = p.tax_status[0] if p.tax_status else None

            # Parse mailing address for residency intelligence
            # Person has primary_address/primary_state for residency
            mailing_addr = None
            mailing_state = None
            is_out_of_state = False

            if ownership and ownership.person:
                person = ownership.person
                mailing_addr = person.primary_address
                mailing_state = person.primary_state
                is_out_of_state = mailing_state is not None and mailing_state != "VT"

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
                mailing_address=mailing_addr,
                mailing_state=mailing_state,
                is_out_of_state=is_out_of_state,
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

        # Get primary owner from PropertyOwnership
        ownership = parcel.property_ownerships[0] if parcel.property_ownerships else None
        owner_name = ownership.as_listed_name if ownership else None
        tax = parcel.tax_status[0] if parcel.tax_status else None

        # Get mailing address from Person if individual owner
        mailing_addr = None
        mailing_state = None
        is_out_of_state = False

        if ownership and ownership.person:
            person = ownership.person
            mailing_addr = person.primary_address
            mailing_state = person.primary_state
            is_out_of_state = mailing_state is not None and mailing_state != "VT"

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
            mailing_address=mailing_addr,
            mailing_state=mailing_state,
            is_out_of_state=is_out_of_state,
        )
    finally:
        db.close()


@warren_agent.tool
def get_dwelling_breakdown(ctx: RunContext[WarrenContext]) -> DwellingBreakdownResult:
    """Get a breakdown of all Warren dwellings by Act 73 tax classification.

    Returns counts of dwellings by:
    - Tax classification (HOMESTEAD, NHS_RESIDENTIAL, NHS_NONRESIDENTIAL)
    - Use type (owner_occupied_primary, short_term_rental, etc.)

    Key insight: A parcel can contain multiple dwelling units.
    For example, a property with homestead + STR has 2 dwellings.
    """
    from sqlalchemy.orm import Session

    with Session(engine) as db:
        total = db.scalar(select(func.count(Dwelling.id))) or 0
        homestead = db.scalar(
            select(func.count(Dwelling.id)).where(Dwelling.tax_classification == "HOMESTEAD")
        ) or 0
        nhs_res = db.scalar(
            select(func.count(Dwelling.id)).where(Dwelling.tax_classification == "NHS_RESIDENTIAL")
        ) or 0
        nhs_nonres = db.scalar(
            select(func.count(Dwelling.id)).where(Dwelling.tax_classification == "NHS_NONRESIDENTIAL")
        ) or 0
        str_count = db.scalar(
            select(func.count(Dwelling.id)).where(Dwelling.str_listing_id.isnot(None))
        ) or 0

        # Use type breakdown
        use_types = db.execute(
            select(Dwelling.use_type, func.count(Dwelling.id))
            .group_by(Dwelling.use_type)
        ).all()
        use_breakdown = {row[0] or "unknown": row[1] for row in use_types}

        # Calculate percentages
        primary_pct = (homestead / total * 100) if total > 0 else 0
        str_pct = (str_count / total * 100) if total > 0 else 0

        return DwellingBreakdownResult(
            total_dwellings=total,
            homestead_count=homestead,
            nhs_residential_count=nhs_res,
            nhs_nonresidential_count=nhs_nonres,
            str_count=str_count,
            headline=f"Warren: {total} dwellings — {primary_pct:.0f}% primary residences, {str_pct:.0f}% STRs",
            use_type_breakdown=use_breakdown,
        )


@warren_agent.tool
def search_dwellings(
    ctx: RunContext[WarrenContext],
    address_contains: str | None = None,
    tax_classification: str | None = None,
    use_type: str | None = None,
    str_only: bool | None = None,
    limit: int = 20,
) -> list[DwellingSummary]:
    """Search for dwelling units with optional filters.

    Args:
        address_contains: Filter by address containing this text
        tax_classification: Filter by Act 73 class (HOMESTEAD, NHS_RESIDENTIAL, NHS_NONRESIDENTIAL)
        use_type: Filter by use (owner_occupied_primary, owner_occupied_secondary, short_term_rental, etc.)
        str_only: If True, only show dwellings with STR listings
        limit: Maximum results (default 20)
    """
    from sqlalchemy.orm import Session

    with Session(engine) as db:
        stmt = (
            select(Dwelling, Parcel, STRListing)
            .join(Parcel, Dwelling.parcel_id == Parcel.id)
            .outerjoin(STRListing, Dwelling.str_listing_id == STRListing.id)
        )

        if address_contains:
            stmt = stmt.where(Parcel.address.ilike(f"%{address_contains}%"))
        if tax_classification:
            stmt = stmt.where(Dwelling.tax_classification == tax_classification)
        if use_type:
            stmt = stmt.where(Dwelling.use_type == use_type)
        if str_only:
            stmt = stmt.where(Dwelling.str_listing_id.isnot(None))

        stmt = stmt.limit(limit)
        rows = db.execute(stmt).all()

        results = []
        for row in rows:
            dwelling, parcel, str_listing = row
            results.append(DwellingSummary(
                id=str(dwelling.id),
                address=parcel.address,
                unit_number=dwelling.unit_number,
                bedrooms=dwelling.bedrooms,
                tax_classification=dwelling.tax_classification,
                use_type=dwelling.use_type,
                is_str=str_listing is not None,
                str_name=str_listing.name if str_listing else None,
                str_price_per_night=str_listing.price_per_night_usd if str_listing else None,
                lat=float(parcel.lat) if parcel.lat else None,
                lng=float(parcel.lng) if parcel.lng else None,
            ))

        return results


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
