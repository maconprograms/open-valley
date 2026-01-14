import { StatsGrid } from "@/components/dashboard";
import SiteLayout from "@/components/SiteLayout";
import Link from "next/link";
import WarrenMapLoader from "@/components/maps/WarrenMapLoader";

interface DashboardStats {
  parcels: {
    count: number;
    total_value: number;
    breakdown?: {
      total: number;
      homestead: {
        count: number;
        percent: number;
      };
      nhs_residential: {
        count: number;
        percent: number;
      };
      other: {
        count: number;
        percent: number;
      };
    };
  };
  dwellings: {
    total: number;
    homestead: {
      count: number;
      percent: number;
    };
    nhs_residential: {
      count: number;
      percent: number;
    };
  };
  str_listings: {
    count: number;
  };
}

async function getStats(): Promise<DashboardStats> {
  const apiUrl = process.env.API_URL || "http://localhost:8999";

  try {
    const res = await fetch(`${apiUrl}/api/stats`, {
      next: { revalidate: 60 },
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch stats: ${res.status}`);
    }

    return res.json();
  } catch (error) {
    console.error("Error fetching stats:", error);
    return {
      parcels: {
        count: 1823,
        total_value: 496000000,
        breakdown: {
          total: 1823,
          homestead: { count: 450, percent: 24.7 },
          nhs_residential: { count: 615, percent: 33.7 },
          other: { count: 758, percent: 41.6 },
        },
      },
      dwellings: {
        total: 2175,
        homestead: { count: 431, percent: 19.8 },
        nhs_residential: { count: 1744, percent: 80.2 },
      },
      str_listings: { count: 605 },
    };
  }
}

export const metadata = {
  title: "Open Valley - Warren Community Intelligence",
  description:
    "Understanding Warren, VT through data. Explore housing patterns, property statistics, and community insights.",
};

export default async function HomePage() {
  const stats = await getStats();

  return (
    <SiteLayout>
      <div className="bg-slate-100">
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* 3D Map Hero Section */}
          <section className="mb-10">
            <WarrenMapLoader
              homesteadCount={stats.dwellings.homestead.count}
              secondHomeCount={stats.dwellings.nhs_residential.count}
              strCount={stats.str_listings.count}
            />
          </section>

          {/* Stats Grid */}
          <section className="mb-10">
            <h2 className="text-2xl font-bold text-slate-900 mb-6">
              Key Statistics
            </h2>
            <StatsGrid stats={stats} />
          </section>

          {/* Context Section */}
          <section className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
            {/* About Warren */}
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">
                About Warren, VT
              </h3>
              <p className="text-slate-600 mb-4">
                Warren is a small town in the Mad River Valley with approximately
                1,800 year-round residents. Home to Sugarbush Resort, Warren has a
                significant second-home population that shapes its community
                character and tax base.
              </p>
              <ul className="space-y-2 text-sm text-slate-600">
                <li className="flex items-start gap-2">
                  <svg
                    className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span>
                    {stats.parcels.count.toLocaleString()} total parcels with{" "}
                    {stats.dwellings.total.toLocaleString()} dwelling units
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <svg
                    className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span>
                    ~${(stats.parcels.total_value / 1_000_000).toFixed(0)}M total
                    assessed property value
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <svg
                    className="w-5 h-5 text-orange-500 mt-0.5 flex-shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                  <span>
                    Only {stats.dwellings.homestead.percent}% of dwellings are
                    primary residences
                  </span>
                </li>
              </ul>
            </div>

            {/* Act 73 Context */}
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">
                Vermont Act 73 of 2025
              </h3>
              <p className="text-slate-600 mb-4">
                Vermont&apos;s new dwelling classification law creates three tax
                categories that will take effect in 2028:
              </p>
              <div className="space-y-3">
                <div className="flex items-start gap-3 p-3 bg-green-50 rounded-lg">
                  <div className="w-3 h-3 mt-1.5 rounded-full bg-green-500 flex-shrink-0" />
                  <div>
                    <p className="font-medium text-green-800">Homestead</p>
                    <p className="text-sm text-green-700">
                      Owner&apos;s primary residence (6+ months/year)
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 bg-orange-50 rounded-lg">
                  <div className="w-3 h-3 mt-1.5 rounded-full bg-orange-500 flex-shrink-0" />
                  <div>
                    <p className="font-medium text-orange-800">NHS Residential</p>
                    <p className="text-sm text-orange-700">
                      Second homes, STRs, vacant dwellings (1-4 units)
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 bg-red-50 rounded-lg">
                  <div className="w-3 h-3 mt-1.5 rounded-full bg-red-500 flex-shrink-0" />
                  <div>
                    <p className="font-medium text-red-800">NHS Non-Residential</p>
                    <p className="text-sm text-red-700">
                      Commercial, long-term rentals, 5+ unit buildings
                    </p>
                  </div>
                </div>
              </div>
              <Link
                href="/learn/glossary"
                className="inline-block mt-4 text-emerald-600 hover:text-emerald-700 text-sm font-medium"
              >
                Learn more about Act 73 &rarr;
              </Link>
            </div>
          </section>

        </main>
      </div>
    </SiteLayout>
  );
}
