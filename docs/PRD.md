# Open Valley: Product Requirements Document

## Executive Summary

Open Valley is a community data platform for the Mad River Valley region of Vermont, designed to strengthen local connections and civic engagement through transparent data sharing and community directory features. The platform serves residents of Warren, Fayston, Waitsfield, Moretown, and Duxbury by providing accessible insights into housing trends, community events, and local contact information.

**Mission**: Strengthen community through data transparency and functional connections.

## Problem Statement

### Primary Problems
1. **Housing Market Opacity**: Residents lack accessible data about property transfers, short-term rental conversions, and housing affordability trends affecting their neighborhoods
2. **Community Coordination Challenges**: Residents need a reliable way to find contact information for neighbors, local groups, and community organizers for practical coordination
3. **Civic Engagement Barriers**: Important town meetings, policy updates, and community decisions happen without broad resident awareness or participation

### Target Impact
- Enable data-driven community conversations about housing and development
- Provide functional directory for community coordination and contact
- Increase civic participation and community engagement

## User Personas & Core User Stories

### Primary Users

**The Concerned Neighbor** (Sarah, 42, Warren resident)
- *"I've noticed more short-term rentals on my street - I want to check the data to see the trend and bring it up at the next town meeting"*
- *"I want to see recent property transfers to understand if my neighborhood is staying affordable for families"*

**The Busy Parent** (Mike, 38, Waitsfield resident)  
- *"I'm rushing between dropoffs and can't remember when the school board meeting is - let me check the calendar quickly"*
- *"I need to find the contact info for other Warren Elementary PTO members for carpooling coordination"*

**The New Resident** (Emma & Jake, 29, recent Warren transplants)
- *"We want to find community events like town meetings to get involved and meet our civic responsibilities"*
- *"We need to find contact information for local groups like the fire department auxiliary to volunteer"*

**The Community Advocate** (Linda, 55, housing advocate)
- *"I want to read policy updates about housing initiatives to stay informed and support good policies"*
- *"I need to find contact information for other community members near the proposed development to coordinate our response"*

## Feature Requirements

### MVP Features (Phase 1)

#### 1. Interactive Property Map
- **Core Functionality**: Mapbox-powered map centered on Mad River Valley
- **Data Display**: Property parcels with homestead status, recent transfers, property types
- **Filtering**: Community-level filtering (Warren, Fayston, Waitsfield, Moretown, Duxbury)
- **User Value**: Visual understanding of housing trends and neighborhood changes

#### 2. Community Directory (Members Only)
- **Authentication**: Manual approval process (future: integrate with Clerk)
- **Profile Features**: Name, contact information (email/phone), town of residence, group affiliations
- **Privacy Controls**: Contact information sharing preferences, member-only access
- **Search Tools**: Search by name, town, or group affiliation
- **User Value**: Functional directory for community coordination and contact (like a phone book)

#### 3. Community Calendar
- **Event Display**: Town meetings, community events, library programs
- **Calendar Interface**: Interactive calendar with event highlighting
- **Event Details**: Time, location, description, organizer contact
- **User Value**: Centralized community event discovery and civic engagement

#### 4. Community Updates
- **Content Types**: Policy changes, housing initiatives, community news
- **Categories**: Policy, data updates, community announcements
- **Sharing**: Individual update pages with shareable URLs
- **User Value**: Stay informed about local decisions and changes

#### 5. Data Transparency
- **Documentation**: Complete data sources, methodology, update frequency
- **API Access**: Public endpoints for community data access
- **Provenance**: Clear attribution and verification processes
- **User Value**: Trust through transparency, enable community research

### Phase 2 Features (Future)

#### Enhanced Authentication & Onboarding
- Clerk integration for seamless signup/login
- Email verification and community referral system
- Automated member verification workflows

#### Advanced Data Features
- Historical trend analysis and visualizations
- Property alert system for neighborhood changes
- Integration with Vermont Open Data Portal
- Mobile app with offline map capabilities

## Content Management Model

**All content is created and maintained by platform administrators.** Users can only update their own contact information in the member directory.

### Administrator-Managed Content
- Community events and calendar entries
- Policy updates and community announcements
- Property data imports and verification
- Member approval and directory management

### User-Managed Content (Limited)
- Personal contact information in member directory
- Privacy settings for contact information sharing
- Group affiliation updates (subject to verification)

This approach ensures content quality and prevents misinformation while maintaining the platform's utility as a trusted community resource.

## Technical Requirements

### Architecture Overview
- **Frontend**: Next.js 14 with App Router, TypeScript, Tailwind CSS
- **Database**: Supabase (PostgreSQL) with Row Level Security
- **Authentication**: Clerk (future) with manual approval workflow
- **Maps**: Mapbox GL JS with custom styling
- **Hosting**: Vercel with automatic deployments

### Map Performance Strategy

To ensure fast loading and smooth interactions for rural Vermont users on 3G connections, Open Valley implements a three-tier map data architecture:

#### Tier 1: Vector Tiles (Base Rendering)
- **Purpose**: Instant parcel visualization with smooth zooming
- **Content**: Parcel boundaries as vector tiles with minimal properties (parcel_id, basic classification)
- **Performance**: Served from Mapbox or self-hosted tile server for sub-second rendering
- **User Benefit**: Immediate visual context of property boundaries across the valley

#### Tier 2: Clustered Points (Overview/Search)  
- **Purpose**: Transfer trend overview without UI overwhelm
- **Content**: Property transfers as dynamically clustered points with aggregated statistics
- **Performance**: Smart clustering based on zoom level prevents rendering thousands of individual points
- **User Benefit**: Quick identification of transfer activity hotspots and neighborhood trends

#### Tier 3: Full GeoJSON (Selected Parcels)
- **Purpose**: Detailed property data loaded only when needed
- **Content**: Complete property details including transfer history, ownership chain, and demographics
- **Performance**: On-demand loading per parcel selection to minimize initial payload
- **User Benefit**: Rich property information without sacrificing map responsiveness

This tiered approach ensures the map loads instantly while providing progressively detailed information as users explore, optimized for Vermont's rural connectivity constraints.

### API Security & Rate Limiting

To protect platform resources and ensure fair access for all users, Open Valley implements comprehensive API security and rate limiting:

#### Rate Limiting Tiers
- **Public Endpoints**: 100 requests/minute per IP address
  - Property data, community events, public updates
  - Sufficient for casual browsing and research
  - Prevents abuse while allowing open access

- **Authenticated Endpoints**: 1,000 requests/minute per user
  - Member directory, detailed property data, user profiles
  - Higher limits for verified community members
  - Supports power users and community organizers

- **Research API Keys**: 5,000 requests/minute per approved researcher
  - Bulk data access for journalists, academics, policy researchers
  - Application process with usage agreement
  - Monitoring and reporting requirements

#### Security Measures
- **CORS Configuration**: Approved domains only for browser-based access
- **API Key Authentication**: Required for external integrations and research access
- **Request Validation**: Input sanitization and schema validation on all endpoints
- **Abuse Detection**: Automatic blocking of suspicious traffic patterns
- **Read-Only Public APIs**: All public API endpoints are read-only to prevent unauthorized content creation

#### CDN & Caching
- **Map Tile Caching**: Mapbox tiles cached through CDN for global performance
- **Static Asset Optimization**: Images and documents served via Vercel Edge Network
- **API Response Caching**: Appropriate cache headers for different data types

This security framework ensures Open Valley remains accessible to the community while protecting against abuse and maintaining performance for all users.

### Intelligent Caching Strategy

To balance performance with data freshness, Open Valley implements tiered caching based on data volatility and user expectations:

#### Cache Aggressively (24hr+)
**Static/Historical Data** - Rarely changes, safe for long-term caching:
- Parcel geometries and zoning boundaries
- Historical property transfer records (>1 year old)
- Community boundaries and geographic features
- Member profile photos and basic info

#### Cache Carefully (5-15 min)
**Semi-Dynamic Data** - Changes periodically, needs moderate freshness:
- Current property ownership status
- Upcoming community events and meeting schedules
- Member online/activity status
- Property market statistics and trends

#### Cache Briefly (1-5 min)
**Dynamic Data** - Changes frequently, requires near real-time updates:
- New policy updates and community announcements
- Recent community posts and discussions
- Active user sessions and authentication tokens
- Real-time event RSVPs and attendance

This caching strategy ensures rural Vermont users experience fast loading times while maintaining data accuracy for time-sensitive community information. Cache invalidation triggers automatically when source data updates, with manual override capabilities for urgent community announcements.

### Database Views for API Performance

To power the composite API endpoints efficiently, Open Valley implements materialized views that pre-compute complex queries and refresh on schedule:

#### Core Performance Views
\`\`\`sql
-- parcel_view: Complete parcel data with ownership and latest transfer
CREATE MATERIALIZED VIEW parcel_view AS
SELECT p.*, u.current_use_classification, e.name as owner_name, 
       pt.transfer_date, pt.sale_price
FROM parcels p
JOIN units u ON p.id = u.parcel_id
JOIN parcel_ownership po ON p.id = po.parcel_id AND po.ownership_end IS NULL
JOIN entities e ON po.entity_id = e.id
LEFT JOIN parcel_transfers pt ON p.id = pt.parcel_id 
WHERE pt.transfer_date = (SELECT MAX(transfer_date) FROM parcel_transfers WHERE parcel_id = p.id);

-- transfer_analytics: Pre-computed transfer statistics by community and time period
CREATE MATERIALIZED VIEW transfer_analytics AS
SELECT community, DATE_TRUNC('month', transfer_date) as month,
       COUNT(*) as transfer_count, AVG(sale_price) as avg_price,
       COUNT(CASE WHEN previous_use != new_use THEN 1 END) as use_changes
FROM parcel_transfers pt
JOIN parcels p ON pt.parcel_id = p.id
GROUP BY community, DATE_TRUNC('month', transfer_date);

-- member_directory_view: Filtered member data with privacy settings applied
CREATE MATERIALIZED VIEW member_directory_view AS
SELECT m.id, m.display_name, m.hometown, m.profile_image_url,
       m.group_affiliations, m.is_full_time_resident,
       CASE WHEN m.privacy_settings->>'show_contact' = 'true' 
            THEN m.contact_info ELSE NULL END as contact_info
FROM members m
WHERE m.is_public = true AND m.approval_status = 'approved';

-- neighborhood_stats: Aggregated metrics by community area
CREATE MATERIALIZED VIEW neighborhood_stats AS
SELECT community, COUNT(*) as total_parcels,
       AVG(CASE WHEN current_use_classification = 'homestead' THEN 1.0 ELSE 0.0 END) * 100 as homestead_percentage,
       AVG(assessed_value) as avg_property_value,
       COUNT(CASE WHEN transfer_date >= CURRENT_DATE - INTERVAL '1 year' THEN 1 END) as ytd_transfers
FROM parcel_view
GROUP BY community;
\`\`\`

#### Refresh Strategy
- **parcel_view**: Refreshes nightly (property ownership changes infrequently)
- **transfer_analytics**: Refreshes weekly (transfer data updated monthly from state sources)
- **member_directory_view**: Refreshes every 15 minutes (members update profiles regularly)
- **neighborhood_stats**: Refreshes daily (provides current community metrics)

These materialized views eliminate complex joins at query time, ensuring sub-second API response times even for data-heavy requests like neighborhood analytics and member directory searches.

### API Design: Composite View Endpoints

Instead of exposing raw database tables, Open Valley provides user journey-driven endpoints that return composed data optimized for specific UI needs:

#### Property & Housing Views
\`\`\`typescript
// GET /api/parcels/view
// Returns parcels with ownership, transfer history, and classification
{
  parcels: [{
    id: string,
    address: string,
    geometry: GeoJSON,
    currentUse: 'homestead' | 'str' | 'ltr' | 'vacant',
    recentTransfers: TransferSummary[],
    ownershipHistory: OwnershipPeriod[],
    assessedValue: number,
    community: string
  }]
}

// GET /api/neighborhoods/view?community=warren
// Aggregated neighborhood statistics and trends
{
  community: string,
  metrics: {
    totalParcels: number,
    homesteadPercentage: number,
    avgPropertyValue: number,
    ytdTransfers: number,
    strConversions: number
  },
  trends: {
    transfersByMonth: ChartData[],
    valueChanges: TrendData[]
  }
}

// GET /api/transfers/recent?limit=50
// Recent property transfers with context
{
  transfers: [{
    parcelId: string,
    address: string,
    transferDate: string,
    salePrice: number,
    previousUse: string,
    newUse: string,
    buyerType: 'individual' | 'llc' | 'trust',
    community: string
  }]
}
\`\`\`

#### Community & Contact Views
\`\`\`typescript
// GET /api/members/directory
// Member profiles with privacy filters applied
{
  members: [{
    id: string,
    displayName: string,
    hometown: string,
    profileImage: string,
    groupAffiliations: string[], // e.g., "Warren Elementary PTO", "Fire Department Auxiliary"
    isFullTimeResident: boolean,
    // Contact info only if user has permission and privacy settings allow
    contactInfo?: {
      email?: string,
      phone?: string
    }
  }]
}

// GET /api/events/upcoming?community=warren&limit=20
// Events with relevant community context
{
  events: [{
    id: string,
    title: string,
    description: string,
    startTime: string,
    location: string,
    category: 'meeting' | 'social' | 'educational',
    community: string,
    organizer: string
  }]
}

// GET /api/updates/feed?category=policy&limit=10
// Policy updates with affected areas
{
  updates: [{
    id: string,
    title: string,
    content: string,
    category: 'policy' | 'data' | 'community',
    publishedAt: string,
    author: string,
    affectedCommunities: string[],
    shareableUrl: string
  }]
}
\`\`\`

#### Data Transparency Views
\`\`\`typescript
// GET /api/data/sources
// Complete data provenance and methodology
{
  sources: [{
    name: string,
    description: string,
    updateFrequency: string,
    lastUpdated: string,
    verificationMethod: string,
    coverage: string[]
  }],
  methodology: {
    dataCollection: string,
    qualityChecks: string[],
    updateProcess: string
  }
}

// GET /api/data/health
// Real-time data quality and freshness metrics
{
  overall: 'healthy' | 'warning' | 'error',
  sources: [{
    name: string,
    status: string,
    lastUpdate: string,
    recordCount: number,
    errorRate: number
  }]
}
\`\`\`

Each endpoint returns composed data that directly supports specific user journeys, eliminating the need for complex client-side data joining and ensuring optimal performance for Vermont's rural connectivity.

### Data Model (Core Tables)
\`\`\`sql
-- Property & Ownership Data
parcels (id, geometry, address, town, zoning_district)
units (id, parcel_id, unit_type, current_use_classification)
entities (id, name, entity_type, contact_info)
parcel_ownership (parcel_id, entity_id, ownership_start, ownership_end)

-- Community Features  
communities (id, name, geometry, community_type)
members (id, clerk_user_id, display_name, contact_info, privacy_settings, group_affiliations)
events (id, title, description, start_time, location, organizer_contact)
updates (id, title, content, category, author, published_at)
\`\`\`

### Performance Requirements
- **Map Loading**: <2 seconds for initial map render
- **Mobile Performance**: Optimized for 3G connections (rural Vermont)
- **Data Freshness**: Property data updated monthly, events updated daily
- **Uptime**: 99.5% availability target

### Security & Privacy
- **Data Protection**: All personal information encrypted at rest
- **Access Control**: Member directory restricted to approved users
- **Privacy First**: Granular privacy controls for all personal data
- **Compliance**: GDPR-compliant data handling and deletion

## Success Metrics

### Engagement Metrics
- **Monthly Active Users**: Target 200+ residents (20% of Warren population)
- **Directory Adoption**: 150+ member profiles within 6 months
- **Event Engagement**: 50+ calendar views per community event
- **Data Usage**: 100+ monthly property map interactions

### Community Impact Metrics
- **Civic Participation**: Increased town meeting attendance (tracked via event views)
- **Community Coordination**: Member-reported successful contact connections for practical needs (carpools, childcare, volunteering)
- **Housing Awareness**: Community discussions referencing platform data
- **Policy Engagement**: Resident engagement with housing policy updates

### Technical Metrics
- **Performance**: <2s average page load time
- **Mobile Usage**: 60%+ of traffic from mobile devices
- **API Usage**: External researchers/journalists using data API
- **Data Quality**: <5% error rate in property data verification

## Timeline & Roadmap

### Phase 1: MVP Launch (Months 1-3)
- **Month 1**: Complete database setup, property data import, basic map functionality
- **Month 2**: Member directory, authentication, calendar features
- **Month 3**: Community updates, data documentation, beta testing with 20 residents

### Phase 2: Community Growth (Months 4-6)
- **Month 4**: Public launch, member onboarding campaign, first town meeting demo
- **Month 5**: Feature refinements based on user feedback, mobile optimization
- **Month 6**: Advanced filtering, API documentation, partnership with local organizations

### Phase 3: Regional Expansion (Months 7-12)
- **Months 7-9**: Expand to full Mad River Valley coverage, enhanced data sources
- **Months 10-12**: Advanced analytics, community-generated content, sustainability planning

## Risk Mitigation

### Technical Risks
- **Data Quality**: Implement automated verification against Vermont state databases
- **Performance**: Progressive loading, caching strategies for rural connectivity
- **Security**: Regular security audits, privacy-by-design architecture

### Community Risks
- **Adoption**: Partner with existing community organizations for promotion
- **Privacy Concerns**: Transparent privacy policies, granular control options
- **Misinformation**: Clear data sourcing, community moderation guidelines

### Operational Risks
- **Maintenance**: Automated data updates, monitoring and alerting systems
- **Scaling**: Cloud-native architecture, performance monitoring
- **Sustainability**: Community funding model, potential municipal partnership

## Success Definition

Open Valley succeeds when:
1. **Residents actively use property data** to participate in informed community discussions about housing and development
2. **Neighbors connect for practical coordination** through the directory, leading to carpools, childcare arrangements, and community organizing
3. **Civic engagement increases** with higher attendance at town meetings and community events
4. **The platform becomes essential community infrastructure** that residents rely on for staying connected and informed

---

*This PRD represents the collective vision for strengthening the Mad River Valley community through technology, transparency, and functional connection.*
