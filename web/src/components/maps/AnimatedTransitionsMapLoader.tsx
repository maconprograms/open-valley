"use client";

import dynamic from "next/dynamic";

const AnimatedTransitionsMap = dynamic(
  () => import("./AnimatedTransitionsMap"),
  {
    ssr: false,
    loading: () => (
      <div className="h-[800px] rounded-2xl bg-slate-800 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-green-400 mx-auto mb-3"></div>
          <span className="text-slate-300">Loading animation...</span>
        </div>
      </div>
    ),
  }
);

export default function AnimatedTransitionsMapLoader() {
  return <AnimatedTransitionsMap />;
}
