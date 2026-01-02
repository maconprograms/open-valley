import Link from "next/link";
import SiteLayout from "@/components/SiteLayout";

export const metadata = {
  title: "Data Sources - Open Valley",
  description: "Explore the raw data sources that power Open Valley's Warren community intelligence.",
};

const dataSources = [
  {
    name: "Vermont Geodata Portal",
    description: "Official state parcel boundaries and property records via ArcGIS REST API.",
    url: "https://geodata.vermont.gov/",
    records: "1,823 Warren parcels",
    updated: "Quarterly",
    fields: ["SPAN", "Address", "Assessed Value", "Property Type", "Boundaries"],
  },
  {
    name: "Vermont Grand List",
    description: "Annual property tax data including homestead declarations and ownership.",
    url: "https://tax.vermont.gov/",
    records: "1,823 properties",
    updated: "Annual (April 1)",
    fields: ["Owner Name", "Mailing Address", "Homestead Filed", "Tax Category"],
  },
  {
    name: "AirROI STR Data",
    description: "Commercial short-term rental listing data from Airbnb and VRBO.",
    url: "https://www.airroi.com/",
    records: "605 Warren listings",
    updated: "Monthly",
    fields: ["Listing ID", "Platform", "Coordinates", "Bedrooms", "Nightly Rate"],
  },
  {
    name: "Front Porch Forum",
    description: "Daily email digests from the Mad River Valley community forum.",
    url: "https://frontporchforum.com/",
    records: "58,174 posts",
    updated: "Daily",
    fields: ["Title", "Content", "Author", "Category", "Date"],
  },
];

export default function DataPage() {
  return (
    <SiteLayout>
      <div className="bg-gray-50 min-h-screen">
        <div className="max-w-4xl mx-auto px-4 py-12">
          <header className="mb-12">
            <h1 className="text-4xl font-bold text-gray-900 mb-4">
              Data Sources
            </h1>
            <p className="text-xl text-gray-600">
              Transparency in how we collect, process, and present Warren community data.
            </p>
          </header>

          {/* Data Sources Grid */}
          <section className="mb-12">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">
              Primary Sources
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
                      <span className="text-gray-500">Records:</span>{" "}
                      <span className="font-medium text-gray-900">{source.records}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Updated:</span>{" "}
                      <span className="font-medium text-gray-900">{source.updated}</span>
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

          {/* Methodology */}
          <section className="mb-12">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">
              Methodology
            </h2>
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-4">
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">
                  Dwelling Classification
                </h3>
                <p className="text-gray-600">
                  We infer dwelling counts from Grand List property descriptions and
                  classify each dwelling according to Vermont&apos;s Act 73 framework:
                  HOMESTEAD (primary residence), NHS_RESIDENTIAL (second homes/STRs),
                  or NHS_NONRESIDENTIAL (commercial/long-term rental).
                </p>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">
                  STR Matching
                </h3>
                <p className="text-gray-600">
                  We match STR listings to parcels using spatial proximity (within 100m
                  of parcel centroid). This achieves a 96% match rate, with uncertain
                  matches flagged for manual review.
                </p>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">
                  Semantic Search
                </h3>
                <p className="text-gray-600">
                  Front Porch Forum posts are embedded using OpenAI&apos;s
                  text-embedding-3-small model and stored in pgvector for
                  semantic similarity search.
                </p>
              </div>
              <Link
                href="/learn/how-we-classify-dwellings"
                className="inline-block mt-4 text-emerald-600 hover:text-emerald-700 text-sm font-medium"
              >
                Read full methodology &rarr;
              </Link>
            </div>
          </section>

          {/* API Access */}
          <section className="mb-12">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">
              API Access
            </h2>
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <p className="text-gray-600 mb-4">
                Open Valley provides a REST API for programmatic access to Warren
                community data. The API is currently in development.
              </p>
              <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm text-gray-300">
                <div className="text-gray-500"># Get dashboard statistics</div>
                <div>curl http://localhost:8999/api/stats</div>
              </div>
              <p className="text-sm text-gray-500 mt-4">
                Full API documentation coming soon.
              </p>
            </div>
          </section>

          {/* Open Source */}
          <section>
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-6">
              <h3 className="font-semibold text-emerald-900 mb-2">
                Open Source Project
              </h3>
              <p className="text-emerald-800 mb-4">
                Open Valley is open source civic technology. View the code,
                report issues, or contribute on GitHub.
              </p>
              <a
                href="https://github.com/maconprograms/open-valley"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 bg-emerald-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-emerald-700 transition-colors"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
                View on GitHub
              </a>
            </div>
          </section>
        </div>
      </div>
    </SiteLayout>
  );
}
