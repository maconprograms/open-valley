"use client";

import dynamic from "next/dynamic";

// Dynamic import for SSR safety (MapLibre requires browser APIs)
const WarrenMap = dynamic(() => import("./WarrenMap"), {
  ssr: false,
  loading: () => (
    <div className="h-[500px] rounded-2xl bg-slate-800 flex items-center justify-center">
      <span className="text-slate-400">Loading 3D map...</span>
    </div>
  ),
});

interface WarrenMapLoaderProps {
  homesteadPercent: number;
  secondHomePercent: number;
  homesteadCount: number;
  secondHomeCount: number;
  strCount: number;
}

export default function WarrenMapLoader(props: WarrenMapLoaderProps) {
  return <WarrenMap {...props} />;
}
