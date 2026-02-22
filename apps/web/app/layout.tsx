import type { Metadata } from "next";
import Link from "next/link";

import { FormValidationController } from "@/components/form-validation-controller";
import { AppNav } from "@/components/nav";
import { buildApiUrl } from "@/lib/api/url";

import "./globals.css";

export const metadata: Metadata = {
  title: "Video Digestor Web",
  description: "Web dashboard for subscriptions, jobs, artifacts and notifications.",
};

type ApiHealthState = "healthy" | "unhealthy" | "unknown";

const HEALTH_TIMEOUT_MS = 1000;

async function fetchApiHealthState(): Promise<ApiHealthState> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);
  try {
    const response = await fetch(buildApiUrl("/healthz"), {
      cache: "no-store",
      signal: controller.signal,
    });
    return response.ok ? "healthy" : "unhealthy";
  } catch {
    return "unknown";
  } finally {
    clearTimeout(timeout);
  }
}

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const healthUrl = buildApiUrl("/healthz");
  const healthState = await fetchApiHealthState();
  const healthLabel =
    healthState === "healthy" ? "Healthy" : healthState === "unhealthy" ? "Degraded" : "Unknown";
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
              <Link href={healthUrl} target="_blank" rel="noreferrer">
                <span className="api-health-chip" aria-live="polite">
                  <span className={`api-health-dot api-health-dot-${healthState}`} aria-hidden="true" />
                  API health: {healthLabel}
                </span>
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
