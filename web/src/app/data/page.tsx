import SiteLayout from "@/components/SiteLayout";
import DataModelDiagram from "@/components/DataModelDiagram";

export const metadata = {
  title: "Data Sources - Open Valley",
  description:
    "Explore the data model and sources that power Open Valley's Warren community intelligence.",
};

interface EntityCounts {
  parcels: number;
  dwellings: number;
  people: number;
  organizations: number;
  property_ownerships: number;
  str_listings: number;
  str_linked_dwellings: number;
}

interface DashboardStats {
  parcels: {
    count: number;
    total_value: number;
  };
  dwellings: {
    total: number;
    homestead: { count: number; percent: number };
    nhs_residential: { count: number; percent: number };
  };
  str_listings: {
    count: number;
    linked_dwellings: number;
  };
  entity_counts: EntityCounts;
}

async function getStats(): Promise<DashboardStats | null> {
  try {
    const res = await fetch("http://localhost:8000/api/stats", {
      next: { revalidate: 3600 }, // Cache for 1 hour
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

// Fallback counts if API is unavailable
const fallbackCounts: EntityCounts = {
  parcels: 1823,
  dwellings: 3109,
  people: 2186,
  organizations: 529,
  property_ownerships: 3079,
  str_listings: 618,
  str_linked_dwellings: 15,
};

const dataSources = [
  {
    name: "Vermont Geodata Portal",
    description:
      "Official state parcel boundaries and property records via ArcGIS REST API.",
    url: "https://geodata.vermont.gov/",
    entity: "Parcels",
    updated: "Quarterly",
    fields: ["SPAN", "Address", "Assessed Value", "Property Type", "Boundaries"],
  },
  {
    name: "Vermont Grand List",
    description:
      "Annual property tax data including homestead declarations, ownership, and dwelling details.",
    url: "https://tax.vermont.gov/",
    entity: "Dwellings, People, Organizations",
    updated: "Annual (April 1)",
    fields: ["Owner Name", "Mailing Address", "Homestead Filed", "Tax Category"],
  },
  {
    name: "AirROI STR Data",
    description:
      "Commercial short-term rental listing data aggregated from Airbnb and VRBO.",
    url: "https://www.airroi.com/",
    entity: "STR Listings",
    updated: "Monthly",
    fields: ["Listing ID", "Platform", "Coordinates", "Bedrooms", "Nightly Rate"],
  },
];

export default async function DataPage() {
  const stats = await getStats();
  const counts = stats?.entity_counts ?? fallbackCounts;

  return (
    <SiteLayout>
      <div className="bg-gray-50 min-h-screen">
        <div className="max-w-4xl mx-auto px-4 py-12">
          <header className="mb-12">
            <h1 className="text-4xl font-bold text-gray-900 mb-4">
              Data Model
            </h1>
            <p className="text-xl text-gray-600">
              Understanding how Warren property data is organized and connected.
            </p>
          </header>

          {/* Interactive Data Model Diagram */}
          <section className="mb-12">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">
              Current Data State
            </h2>
            <DataModelDiagram counts={counts} />
            {!stats && (
              <p className="text-sm text-gray-500 mt-2 italic">
                Live data unavailable. Showing cached values.
              </p>
            )}
          </section>

          {/* Data Sources Grid */}
          <section className="mb-12">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">
              Data Sources
            </h2>
            <div className="space-y-6">
              {dataSources.map((source) => (
                <div
                  key={source.name}
                  className="bg-white rounded-lg shadow-sm border border-gray-200 p-6"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        {source.name}
                      </h3>
                      <p className="text-gray-600 mt-1">{source.description}</p>
                    </div>
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-emerald-600 hover:text-emerald-700 text-sm font-medium whitespace-nowrap"
                    >
                      Visit source &rarr;
                    </a>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">Provides:</span>{" "}
                      <span className="font-medium text-gray-900">
                        {source.entity}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">Updated:</span>{" "}
                      <span className="font-medium text-gray-900">
                        {source.updated}
                      </span>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {source.fields.map((field) => (
                      <span
                        key={field}
                        className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded"
                      >
                        {field}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>

        </div>
      </div>
    </SiteLayout>
  );
}
