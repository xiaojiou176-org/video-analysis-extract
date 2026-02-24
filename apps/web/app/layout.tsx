import type { Metadata } from "next";
import Link from "next/link";

import { FormValidationController } from "@/components/form-validation-controller";
import { AppNav } from "@/components/nav";
import { buildApiUrl } from "@/lib/api/url";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "AI 信息中枢",
    template: "%s — AI 信息中枢",
  },
  description: "订阅、任务、产物与通知管理后台",
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
    healthState === "healthy" ? "正常" : healthState === "unhealthy" ? "异常" : "未知";
  return (
    <html lang="zh-Hans">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+SC:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <a className="skip-link" href="#main-content">
          跳至主内容
        </a>
        <div className="page-shell">
          <FormValidationController />
          <header className="top-header">
            <div>
              <p className="eyebrow">AI 信息中枢</p>
              <h1 className="site-title">控制台</h1>
            </div>
            <div className="header-links">
              <Link href={healthUrl} target="_blank" rel="noreferrer">
                <span className="api-health-chip" aria-live="polite">
                  <span className={`api-health-dot api-health-dot-${healthState}`} aria-hidden="true" />
                  API 状态：{healthLabel}
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
