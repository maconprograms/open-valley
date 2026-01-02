import Navigation from "./Navigation";
import Footer from "./Footer";

interface SiteLayoutProps {
  children: React.ReactNode;
  showFooter?: boolean;
}

/**
 * Shared layout for pages with navigation.
 * The explore (chat) page uses a different layout without footer.
 */
export default function SiteLayout({
  children,
  showFooter = true,
}: SiteLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col">
      <Navigation />
      <main className="flex-1">{children}</main>
      {showFooter && <Footer />}
    </div>
  );
}
