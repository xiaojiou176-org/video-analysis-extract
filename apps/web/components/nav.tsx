"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "首页" },
  { href: "/subscriptions", label: "订阅管理" },
  { href: "/jobs", label: "任务" },
  { href: "/feed", label: "AI 摘要" },
  { href: "/artifacts", label: "产物" },
  { href: "/settings", label: "设置" },
];

export function AppNav() {
  const pathname = usePathname();

  return (
    <div className="app-nav-shell">
      <nav aria-label="Main navigation" className="app-nav">
        {NAV_ITEMS.map((item) => {
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={active ? "nav-link nav-link-active" : "nav-link"}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
