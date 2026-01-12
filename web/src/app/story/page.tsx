import AnimatedTransitionsMapLoader from "@/components/maps/AnimatedTransitionsMapLoader";

export const metadata = {
  title: "De-Homesteading Warren | Open Valley",
  description: "Watch as homesteads become non-homesteads, year by year",
};

export default function StoryPage() {
  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <a href="/" className="flex items-center gap-2 text-white hover:text-green-400 transition-colors">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                <span className="font-medium">Back to Dashboard</span>
              </a>
            </div>
            <div className="text-slate-400 text-sm">
              Open Valley | Warren Housing Intelligence
            </div>
          </div>
        </div>
      </header>

      {/* Intro section */}
      <section className="max-w-4xl mx-auto px-4 py-12 text-center">
        <h1 className="text-4xl font-bold text-white mb-4">
          De-Homesteading Warren
        </h1>
        <p className="text-xl text-slate-400 mb-2">
          How homesteads become non-homesteads, one transaction at a time
        </p>
        <p className="text-slate-500 max-w-2xl mx-auto">
          This animation shows property transfers from 2019-2025, tracking <em>actual status changes</em>:
          homes that <span className="text-green-400">became homesteads</span> (converted from non-homestead
          to homestead) and those that <span className="text-red-400">lost homestead status</span>
          (converted from homestead to non-homestead).
        </p>
      </section>

      {/* Map section */}
      <section className="max-w-7xl mx-auto px-4 pb-12">
        <AnimatedTransitionsMapLoader />
      </section>

      {/* Context section */}
      <section className="bg-slate-800 border-t border-slate-700">
        <div className="max-w-4xl mx-auto px-4 py-12">
          <h2 className="text-2xl font-bold text-white mb-6">Understanding the Data</h2>

          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <h3 className="text-lg font-semibold text-white mb-3">What is a &ldquo;Homestead&rdquo;?</h3>
              <p className="text-slate-400">
                In Vermont, a homestead is your primary residence—where you live at least
                6 months per year. Property owners must declare homestead status for tax purposes.
                Warren&apos;s current homestead rate is just <span className="text-green-400 font-bold">16.4%</span>.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-red-500"></span>
                Lost Homestead (TRUE_LOSS)
              </h3>
              <p className="text-slate-400">
                A VT seller (was likely homesteading) sells to a buyer who declares &ldquo;secondary residence&rdquo;
                or &ldquo;non-primary&rdquo; intent. <strong className="text-white">The home converts from homestead to non-homestead.</strong>
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-green-500"></span>
                Became Homestead (TRUE_GAIN)
              </h3>
              <p className="text-slate-400">
                An out-of-state seller (was non-homestead) sells to a buyer who declares &ldquo;primary residence&rdquo;.
                <strong className="text-white"> The home converts from non-homestead to homestead.</strong>
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-blue-500"></span>
                Stayed Homestead
              </h3>
              <p className="text-slate-400">
                A VT seller (homestead) sells to a buyer who will also use it as homestead.
                <span className="text-slate-500"> No net change to Warren&apos;s homestead count.</span>
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-slate-400"></span>
                Stayed Non-Homestead
              </h3>
              <p className="text-slate-400">
                An out-of-state seller (non-homestead) sells to another non-homestead buyer.
                <span className="text-slate-500"> No net change to Warren&apos;s homestead count.</span>
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white mb-3">Data Coverage</h3>
              <p className="text-slate-400">
                The animation shows ~93% of transfers (those with coordinates in PTTR data).
                The remaining ~7% are mostly timeshare intervals without geocoded locations.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Stats section */}
      <section className="max-w-4xl mx-auto px-4 py-12">
        <h2 className="text-2xl font-bold text-white mb-6 text-center">Actual Status Changes (2019-2025)</h2>
        <p className="text-slate-400 text-center mb-6 text-sm max-w-2xl mx-auto">
          This table shows only transfers that <em>changed</em> a home&apos;s status — excluding
          homestead→homestead and non-homestead→non-homestead transfers that have no net effect.
        </p>

        <div className="bg-slate-800 rounded-xl overflow-hidden">
          <table className="w-full text-left">
            <thead className="bg-slate-700">
              <tr>
                <th className="px-4 py-3 text-slate-300 font-medium">Year</th>
                <th className="px-4 py-3 text-slate-300 font-medium text-right">Lost Homestead</th>
                <th className="px-4 py-3 text-slate-300 font-medium text-right">Became Homestead</th>
                <th className="px-4 py-3 text-slate-300 font-medium text-right">Net</th>
                <th className="px-4 py-3 text-slate-300 font-medium text-center">Trend</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {[
                { year: 2019, losses: 30, gains: 11, net: -19 },
                { year: 2020, losses: 40, gains: 20, net: -20 },
                { year: 2021, losses: 34, gains: 10, net: -24 },
                { year: 2022, losses: 19, gains: 6, net: -13 },
                { year: 2023, losses: 21, gains: 3, net: -18 },
                { year: 2024, losses: 25, gains: 13, net: -12 },
                { year: 2025, losses: 15, gains: 12, net: -3 },
              ].map((row) => (
                <tr key={row.year} className="text-white">
                  <td className="px-4 py-3 font-medium">{row.year}</td>
                  <td className="px-4 py-3 text-right text-red-400">-{row.losses}</td>
                  <td className="px-4 py-3 text-right text-green-400">+{row.gains}</td>
                  <td className={`px-4 py-3 text-right font-bold ${row.net >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {row.net >= 0 ? '+' : ''}{row.net}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="inline-block px-2 py-0.5 rounded text-xs bg-red-500/20 text-red-400">
                      Losing Homesteads
                    </span>
                  </td>
                </tr>
              ))}
              <tr className="bg-slate-700 text-white font-bold">
                <td className="px-4 py-3">Total</td>
                <td className="px-4 py-3 text-right text-red-400">-184</td>
                <td className="px-4 py-3 text-right text-green-400">+75</td>
                <td className="px-4 py-3 text-right text-red-400">-109</td>
                <td className="px-4 py-3 text-center">
                  <span className="inline-block px-2 py-0.5 rounded text-xs bg-red-500/20 text-red-400">
                    Net Loss
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <p className="text-slate-500 text-center mt-4 text-sm">
          Source: Vermont Property Transfer Tax Returns (PTTR) — geocoded transfers only
        </p>
      </section>

      {/* Footer */}
      <footer className="bg-slate-800 border-t border-slate-700 py-8">
        <div className="max-w-4xl mx-auto px-4 text-center text-slate-500 text-sm">
          <p>
            Data from Vermont Grand List and Property Transfer Tax Returns.
            <br />
            Analysis by <a href="/" className="text-green-400 hover:underline">Open Valley</a> | January 2026
          </p>
        </div>
      </footer>
    </div>
  );
}
