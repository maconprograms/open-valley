"use client";

import { useState, useEffect, ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface AdminLayoutProps {
  children: ReactNode;
}

export default function AdminLayout({ children }: AdminLayoutProps) {
  const pathname = usePathname();
  const [token, setToken] = useState<string>("");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check for stored token on mount
  useEffect(() => {
    const storedToken = localStorage.getItem("admin_token");
    if (storedToken) {
      validateToken(storedToken);
    } else {
      setIsLoading(false);
    }
  }, []);

  const validateToken = async (tokenToValidate: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/api/admin/str-review/stats`, {
        headers: {
          Authorization: `Bearer ${tokenToValidate}`,
        },
      });

      if (response.ok) {
        localStorage.setItem("admin_token", tokenToValidate);
        setToken(tokenToValidate);
        setIsAuthenticated(true);
      } else if (response.status === 401 || response.status === 403) {
        setError("Invalid admin token");
        localStorage.removeItem("admin_token");
      } else {
        setError("Failed to connect to API");
      }
    } catch {
      setError("Failed to connect to API. Is the server running?");
    }
    setIsLoading(false);
  };

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    validateToken(token);
  };

  const handleLogout = () => {
    localStorage.removeItem("admin_token");
    setToken("");
    setIsAuthenticated(false);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-400 mx-auto mb-3"></div>
          <span className="text-slate-300">Authenticating...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="bg-slate-800 p-8 rounded-xl shadow-xl max-w-md w-full mx-4">
          <div className="text-center mb-6">
            <span className="text-3xl">🔐</span>
            <h1 className="text-xl font-bold text-white mt-2">Admin Access</h1>
            <p className="text-slate-400 text-sm mt-1">
              Enter your admin token to continue
            </p>
          </div>

          <form onSubmit={handleLogin}>
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Admin token"
              className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
              autoFocus
            />
            {error && (
              <p className="text-red-400 text-sm mt-2">{error}</p>
            )}
            <button
              type="submit"
              className="w-full mt-4 px-4 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-lg transition-colors"
            >
              Authenticate
            </button>
          </form>

          <div className="mt-6 pt-4 border-t border-slate-700">
            <Link
              href="/"
              className="flex items-center justify-center gap-2 text-slate-400 hover:text-white text-sm transition-colors"
            >
              <span>←</span>
              <span>Back to Open Valley</span>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const navItems = [
    { href: "/admin/str-review", label: "STR Review", icon: "🏠" },
  ];

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col">
      {/* Admin Navigation */}
      <nav className="bg-slate-800 border-b border-slate-700 sticky top-0 z-50">
        <div className="px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-14">
            {/* Logo */}
            <div className="flex items-center">
              <Link href="/" className="flex items-center space-x-2 mr-8">
                <span className="text-xl">🏔️</span>
                <span className="font-bold text-white">Open Valley</span>
                <span className="bg-amber-600 text-white text-xs px-2 py-0.5 rounded font-medium">
                  ADMIN
                </span>
              </Link>

              {/* Nav Links */}
              <div className="flex items-center space-x-1">
                {navItems.map((item) => {
                  const isActive = pathname.startsWith(item.href);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`
                        px-3 py-2 rounded-md text-sm font-medium transition-colors
                        ${
                          isActive
                            ? "bg-emerald-600 text-white"
                            : "text-slate-300 hover:bg-slate-700 hover:text-white"
                        }
                      `}
                    >
                      <span className="mr-1.5">{item.icon}</span>
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>

            {/* Right side */}
            <div className="flex items-center space-x-4">
              <Link
                href="/"
                className="text-slate-400 hover:text-white text-sm transition-colors"
              >
                ← Back to Site
              </Link>
              <button
                onClick={handleLogout}
                className="text-slate-400 hover:text-red-400 text-sm transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1">{children}</main>
    </div>
  );
}
