"use client";

import Link from "next/link";

interface DashboardStats {
  parcels: {
    count: number;
    total_value: number;
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

interface DashboardHeroProps {
  stats: DashboardStats;
}

export default function DashboardHero({ stats }: DashboardHeroProps) {
  const homesteadPct = stats.dwellings.homestead.percent;
  const secondHomePct = stats.dwellings.nhs_residential.percent;

  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-800 via-slate-900 to-slate-800 text-white">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-10">
        <svg className="h-full w-full" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern
              id="grid"
              width="32"
              height="32"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M 32 0 L 0 0 0 32"
                fill="none"
                stroke="white"
                strokeWidth="0.5"
              />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>

      <div className="relative px-8 py-12 md:py-16">
        {/* Main headline */}
        <div className="max-w-4xl">
          <p className="text-green-400 font-medium uppercase tracking-wider text-sm mb-2">
            Warren, Vermont
          </p>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight">
            <span className="text-green-400">{homesteadPct}%</span> Primary Residences
            <br />
            <span className="text-orange-400">{secondHomePct}%</span> Second Homes
          </h1>
          <p className="mt-6 text-xl text-slate-300 max-w-2xl">
            Explore how Vermont&apos;s Act 73 dwelling classifications will reshape
            property taxation in our mountain community.
          </p>
        </div>

        {/* Visual breakdown bar */}
        <div className="mt-10 max-w-2xl">
          <div className="h-4 rounded-full overflow-hidden flex shadow-inner bg-slate-700">
            <div
              className="bg-green-500 transition-all duration-700 ease-out"
              style={{ width: `${homesteadPct}%` }}
              title={`Primary Residences: ${homesteadPct}%`}
            />
            <div
              className="bg-orange-500 transition-all duration-700 ease-out"
              style={{ width: `${secondHomePct}%` }}
              title={`Second Homes: ${secondHomePct}%`}
            />
          </div>
          <div className="flex justify-between mt-2 text-sm text-slate-400">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-green-500" />
              <span>Homestead ({stats.dwellings.homestead.count.toLocaleString()})</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-orange-500" />
              <span>NHS Residential ({stats.dwellings.nhs_residential.count.toLocaleString()})</span>
            </div>
          </div>
        </div>

        {/* STR callout */}
        {stats.str_listings.count > 0 && (
          <div className="mt-8 inline-flex items-center gap-3 bg-slate-700/50 rounded-lg px-4 py-2">
            <span className="text-red-400 font-bold text-2xl">
              {stats.str_listings.count}
            </span>
            <span className="text-slate-300">
              Active short-term rental listings
            </span>
          </div>
        )}

        {/* Quick links */}
        <div className="mt-10 flex flex-wrap gap-4">
          <Link
            href="/explore"
            className="inline-flex items-center gap-2 bg-green-600 hover:bg-green-500 text-white px-6 py-3 rounded-lg font-medium transition-colors"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
              />
            </svg>
            Explore with AI
          </Link>
          <a
            href="https://legislature.vermont.gov/bill/status/2026/H.454"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white px-6 py-3 rounded-lg font-medium transition-colors"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
              />
            </svg>
            Learn About Act 73
          </a>
          <a
            href="https://geodata.vermont.gov/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white px-6 py-3 rounded-lg font-medium transition-colors"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"
              />
            </svg>
            View Data Sources
          </a>
        </div>
      </div>
    </div>
  );
}
