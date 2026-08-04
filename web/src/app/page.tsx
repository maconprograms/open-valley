import BaselineDashboard from "@/components/baseline/BaselineDashboard";

export const metadata = {
  title: "Open Valley — Warren baseline",
  description: "Evidence-first property and housing baseline for Warren, Vermont.",
};

export default function HomePage() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <BaselineDashboard />
    </main>
  );
}
