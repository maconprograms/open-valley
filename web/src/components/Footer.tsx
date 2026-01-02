import Link from "next/link";

export default function Footer() {
  return (
    <footer className="bg-gray-50 border-t border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* About */}
          <div className="col-span-1 md:col-span-2">
            <h3 className="font-semibold text-gray-900 mb-2">Open Valley</h3>
            <p className="text-sm text-gray-600 mb-4">
              Understanding Warren, VT through data. Only 20% of dwellings are
              primary residences — we&apos;re making housing patterns visible to
              help residents and policymakers make informed decisions.
            </p>
            <p className="text-xs text-gray-500">
              Data from Vermont Geodata Portal, Grand List, AirROI, and Front
              Porch Forum.
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="font-semibold text-gray-900 mb-2">Explore</h3>
            <ul className="space-y-1 text-sm">
              <li>
                <Link
                  href="/explore"
                  className="text-gray-600 hover:text-emerald-600"
                >
                  Chat with AI
                </Link>
              </li>
              <li>
                <Link
                  href="/learn"
                  className="text-gray-600 hover:text-emerald-600"
                >
                  Research & Articles
                </Link>
              </li>
              <li>
                <Link
                  href="/data"
                  className="text-gray-600 hover:text-emerald-600"
                >
                  Data Sources
                </Link>
              </li>
            </ul>
          </div>

          {/* Policy Context */}
          <div>
            <h3 className="font-semibold text-gray-900 mb-2">Policy Context</h3>
            <ul className="space-y-1 text-sm">
              <li>
                <Link
                  href="/learn/understanding-act-73"
                  className="text-gray-600 hover:text-emerald-600"
                >
                  Vermont Act 73
                </Link>
              </li>
              <li>
                <a
                  href="https://mrvpd.org/housing/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-600 hover:text-emerald-600"
                >
                  MRV Housing Coalition ↗
                </a>
              </li>
              <li>
                <a
                  href="https://vcgi.vermont.gov/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-600 hover:text-emerald-600"
                >
                  Vermont Geodata ↗
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-gray-200 text-center text-xs text-gray-500">
          <p>
            Built with{" "}
            <a
              href="https://ai.pydantic.dev"
              className="text-emerald-600 hover:underline"
            >
              Pydantic AI
            </a>{" "}
            +{" "}
            <a
              href="https://nextjs.org"
              className="text-emerald-600 hover:underline"
            >
              Next.js
            </a>{" "}
            • Open source civic tech for Warren, VT
          </p>
        </div>
      </div>
    </footer>
  );
}
