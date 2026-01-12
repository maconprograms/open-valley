import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import "@copilotkit/react-ui/styles.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Open Valley - Warren Property Intelligence",
  description: "Conversational AI for exploring Warren, VT property data",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8999";

  return (
    <html lang="en">
      <head>
        {/* Prefetch GeoJSON data for map - starts fetching while page loads */}
        <link
          rel="prefetch"
          href={`${apiUrl}/api/parcels/geojson`}
          as="fetch"
          crossOrigin="anonymous"
        />
        <link
          rel="prefetch"
          href={`${apiUrl}/api/dwellings/geojson`}
          as="fetch"
          crossOrigin="anonymous"
        />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
