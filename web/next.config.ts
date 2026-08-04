import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Proxy the standalone evidence-ledger API in production.
  async rewrites() {
    const baselineApiUrl = process.env.INTERNAL_BASELINE_API_URL || "http://localhost:8998";
    return [
      {
        source: "/api/baseline/:path*",
        destination: `${baselineApiUrl}/api/baseline/:path*`,
      },
    ];
  },
};

export default nextConfig;
