import type { Metadata } from "next";
import Link from "next/link";

import { FormValidationController } from "@/components/form-validation-controller";
import { AppNav } from "@/components/nav";

import "./globals.css";

export const metadata: Metadata = {
  title: "Video Digestor Web",
  description: "Web dashboard for subscriptions, jobs, artifacts and notifications.",
};

type ApiHealthState = "healthy" | "unhealthy" | "unknown";

function resolveApiBaseUrl(): string {
  const base =
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    process.env.VD_API_BASE_URL ??
    "http://127.0.0.1:8000";
  return base.replace(/\/$/, "");
}

async function fetchApiHealthState(): Promise<ApiHealthState> {
  const endpoint = `${resolveApiBaseUrl()}/healthz`;
  try {
    const response = await fetch(endpoint, { cache: "no-store" });
    return response.ok ? "healthy" : "unhealthy";
  } catch {
    return "unknown";
  }
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const healthPromise = fetchApiHealthState();
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main-content">
          Skip to content
        </a>
        <div className="page-shell">
          <FormValidationController />
          <header className="top-header">
            <div>
              <p className="eyebrow">Video Digestor</p>
              <h1 className="site-title">Operations Console</h1>
            </div>
            <div className="header-links">
              <Link href={`${resolveApiBaseUrl()}/healthz`} target="_blank" rel="noreferrer">
                <ApiHealthChip healthPromise={healthPromise} />
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

async function ApiHealthChip({ healthPromise }: { healthPromise: Promise<ApiHealthState> }) {
  const status = await healthPromise;
  const label = status === "healthy" ? "Healthy" : status === "unhealthy" ? "Degraded" : "Unknown";
  return (
    <span className="api-health-chip" aria-live="polite">
      <span className={`api-health-dot api-health-dot-${status}`} aria-hidden="true" />
      API health: {label}
    </span>
  );
}
