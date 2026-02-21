import type { Metadata } from "next";
import Link from "next/link";

import { AppNav } from "@/components/nav";

import "./globals.css";

export const metadata: Metadata = {
  title: "Video Digestor Web",
  description: "Web dashboard for subscriptions, jobs, artifacts and notifications.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main-content">
          Skip to content
        </a>
        <div className="page-shell">
          <header className="top-header">
            <div>
              <p className="eyebrow">Video Digestor</p>
              <h1 className="site-title">Operations Console</h1>
            </div>
            <div className="header-links">
              <Link href="http://127.0.0.1:8000/healthz" target="_blank" rel="noreferrer">
                API Health
              </Link>
            </div>
          </header>

          <AppNav />

          <main id="main-content" className="main-content">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
