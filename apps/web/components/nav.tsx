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
	const activeItem = NAV_ITEMS.find((item) =>
		item.href === "/" ? pathname === "/" : pathname.startsWith(item.href),
	);

	return (
		<div className="app-nav-shell">
			<nav aria-label="主导航" aria-describedby="app-nav-status" className="app-nav">
				{NAV_ITEMS.map((item) => {
					const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
					return (
						<Link
							key={item.href}
							href={item.href}
							className={active ? "nav-link nav-link-active card-interactive" : "nav-link card-interactive"}
							aria-current={active ? "page" : undefined}
							data-interaction="link-muted"
						>
							{item.label}
						</Link>
					);
				})}
			</nav>
			<output id="app-nav-status" className="sr-only" role="status" aria-live="polite" aria-atomic="true">
				当前页面：{activeItem?.label ?? "未知"}
			</output>
		</div>
	);
}
