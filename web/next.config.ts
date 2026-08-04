import type { NextConfig } from "next";
import createMDX from "@next/mdx";

const nextConfig: NextConfig = {
  // Support MDX files as pages
  pageExtensions: ["js", "jsx", "md", "mdx", "ts", "tsx"],

  // Proxy API requests to FastAPI backend in production
  async rewrites() {
    const legacyApiUrl = process.env.INTERNAL_API_URL || "http://localhost:8999";
    const baselineApiUrl = process.env.INTERNAL_BASELINE_API_URL || "http://localhost:8998";
    return [
      {
        source: "/api/baseline/:path*",
        destination: `${baselineApiUrl}/api/baseline/:path*`,
      },
      {
        source: "/api/:path*",
        destination: `${legacyApiUrl}/:path*`,
      },
    ];
  },
};

const withMDX = createMDX({
  // Add markdown plugins here if needed
  options: {
    remarkPlugins: [],
    rehypePlugins: [],
  },
});

export default withMDX(nextConfig);
