"use client";

import { useEffect, useMemo, useRef, type ReactNode } from "react";
import { usePathname } from "next/navigation";

type RouteTransitionProps = {
	children: ReactNode;
};

const ROUTE_NAME_MAP: Array<{ href: string; label: string }> = [
	{ href: "/", label: "首页" },
	{ href: "/subscriptions", label: "订阅管理" },
	{ href: "/jobs", label: "任务" },
	{ href: "/feed", label: "AI 摘要" },
	{ href: "/settings", label: "设置" },
];

function getRouteLabel(pathname: string | null): string {
	const normalizedPath = pathname ?? "/";
	for (const route of ROUTE_NAME_MAP) {
		if (
			route.href === "/"
				? normalizedPath === "/"
				: normalizedPath === route.href || normalizedPath.startsWith(`${route.href}/`)
		) {
			return route.label;
		}
	}
	return "页面";
}

export function RouteTransition({ children }: RouteTransitionProps) {
	const pathname = usePathname();
	const transitionRef = useRef<HTMLDivElement>(null);
	const routeLabel = useMemo(() => getRouteLabel(pathname), [pathname]);
	const lastFocusedHeadingRef = useRef<HTMLElement | null>(null);

	useEffect(() => {
		const transitionElement = transitionRef.current;
		if (!transitionElement) {
			return;
		}

		const focusMainHeading = () => {
			let targetHeading: HTMLElement | null = null;
			const selectors = ["[data-route-heading]", "h1", "h2"];
			for (const selector of selectors) {
				targetHeading = transitionElement.querySelector<HTMLElement>(selector);
				if (targetHeading) {
					break;
				}
			}
			if (!targetHeading) {
				return;
			}

			const prev = lastFocusedHeadingRef.current;
			if (prev && prev !== targetHeading) {
				prev.removeAttribute("tabindex");
			}

			if (!targetHeading.hasAttribute("tabindex")) {
				targetHeading.setAttribute("tabindex", "-1");
			}
			lastFocusedHeadingRef.current = targetHeading;
			targetHeading.focus({ preventScroll: true });
		};

		const frameId = window.requestAnimationFrame(focusMainHeading);
		return () => {
			window.cancelAnimationFrame(frameId);
			const prev = lastFocusedHeadingRef.current;
			if (prev) {
				prev.removeAttribute("tabindex");
				lastFocusedHeadingRef.current = null;
			}
		};
	}, [pathname]);

	return (
		<div
			ref={transitionRef}
			key={pathname}
			className="route-transition route-transition-enter folo-route-layer"
			data-route={pathname}
		>
			<div aria-hidden="true" className="route-progress-indicator">
				<div aria-hidden="true" className="route-progress-bar" />
			</div>
			<p className="sr-only" role="status" aria-live="polite" aria-atomic="true">
				已切换到：{routeLabel}
			</p>
			{children}
		</div>
	);
}
