"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Home, List, ListTodo, Menu, PanelLeftClose, Plus, Settings, Sparkles } from "lucide-react";

import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Sheet, SheetContent, SheetDescription, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import type { Subscription, SubscriptionCategory } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const CATEGORY_ORDER: SubscriptionCategory[] = ["tech", "creator", "macro", "ops", "misc"];
const CATEGORY_LABELS: Record<SubscriptionCategory, string> = {
	tech: "科技",
	creator: "创作者",
	macro: "宏观",
	ops: "运维",
	misc: "其他",
};

function groupByCategory(subs: Subscription[]): Map<SubscriptionCategory, Subscription[]> {
	const map = new Map<SubscriptionCategory, Subscription[]>();
	for (const cat of CATEGORY_ORDER) {
		map.set(cat, []);
	}
	for (const sub of subs) {
		const cat = sub.category in CATEGORY_LABELS ? (sub.category as SubscriptionCategory) : "misc";
		const list = map.get(cat) ?? [];
		list.push(sub);
		map.set(cat, list);
	}
	return map;
}

type ApiHealthState = "healthy" | "unhealthy" | "timeout_or_unknown";

type SidebarProps = {
	subscriptions: Subscription[];
	subscriptionsLoadError?: boolean;
	apiHealthState: ApiHealthState;
	apiHealthUrl: string;
	apiHealthLabel: string;
};

type NavContentProps = {
	collapsed: boolean;
	subscriptions: Subscription[];
	subscriptionsLoadError: boolean;
	apiHealthState: ApiHealthState;
	apiHealthUrl: string;
	apiHealthLabel: string;
};

function SidebarNavContent({
	collapsed,
	subscriptions,
	subscriptionsLoadError,
	apiHealthState,
	apiHealthUrl,
	apiHealthLabel,
}: NavContentProps) {
	const pathname = usePathname();
	const searchParams = useSearchParams();
	const currentCategory = searchParams.get("category") ?? "";
	const currentSub = searchParams.get("sub") ?? "";
	const isFeed = pathname === "/feed" || pathname.startsWith("/feed");
	const grouped = groupByCategory(subscriptions);
	const enabledSubs = subscriptions.filter((s) => s.enabled);

	return (
			<>
				<nav aria-label="主导航" className="flex flex-col gap-0.5 p-3">
				<Link
					href="/"
					className={cn(
						"flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200 motion-reduce:transition-none",
						pathname === "/"
							? "bg-sidebar-accent text-sidebar-accent-foreground"
							: "text-sidebar-foreground/90 hover:bg-sidebar-accent/70 hover:text-sidebar-accent-foreground",
					)}
					aria-current={pathname === "/" ? "page" : undefined}
				>
					<Home className="size-4 shrink-0 opacity-80" aria-hidden />
					<span className={collapsed ? "sr-only" : undefined}>首页</span>
				</Link>
				<Link
					href="/feed"
					className={cn(
						"flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200 motion-reduce:transition-none",
						isFeed && !currentCategory && !currentSub
							? "bg-sidebar-accent text-sidebar-accent-foreground"
							: "text-sidebar-foreground/90 hover:bg-sidebar-accent/70 hover:text-sidebar-accent-foreground",
					)}
					aria-current={isFeed && !currentCategory && !currentSub ? "page" : undefined}
				>
					<Sparkles className="size-4 shrink-0 opacity-80" aria-hidden />
					<span className={collapsed ? "sr-only" : undefined}>AI 摘要</span>
				</Link>
				<Link
					href="/jobs"
					className={cn(
						"flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200 motion-reduce:transition-none",
						pathname.startsWith("/jobs")
							? "bg-sidebar-accent text-sidebar-accent-foreground"
							: "text-sidebar-foreground/90 hover:bg-sidebar-accent/70 hover:text-sidebar-accent-foreground",
					)}
					aria-current={pathname.startsWith("/jobs") ? "page" : undefined}
				>
					<ListTodo className="size-4 shrink-0 opacity-80" aria-hidden />
					<span className={collapsed ? "sr-only" : undefined}>任务</span>
				</Link>

				{subscriptionsLoadError && !collapsed ? (
					<div
						className="mx-1 mt-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2"
						role="status"
						aria-live="polite"
					>
						<p className="text-xs text-destructive">订阅列表加载失败，可在订阅管理中重试。</p>
						<Link
							href="/subscriptions"
							className="mt-1 inline-flex text-xs font-medium text-destructive underline underline-offset-2"
						>
							前往订阅管理
						</Link>
					</div>
				) : null}

				{enabledSubs.length > 0 && !collapsed ? (
					<>
						<Separator className="my-2" />
						{CATEGORY_ORDER.map((cat) => {
							const list = grouped.get(cat)?.filter((s) => s.enabled) ?? [];
							if (list.length === 0) return null;
							return (
								<div key={cat} className="space-y-0.5">
									<Link
										href={`/feed?category=${cat}`}
										className={cn(
											"flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition-all duration-200 motion-reduce:transition-none",
											currentCategory === cat
												? "bg-sidebar-accent text-sidebar-accent-foreground"
												: "text-muted-foreground hover:bg-sidebar-accent/70 hover:text-sidebar-accent-foreground",
										)}
										aria-current={currentCategory === cat ? "page" : undefined}
									>
										<List className="size-3 shrink-0 opacity-70" aria-hidden />
										{CATEGORY_LABELS[cat]}
									</Link>
									<ul className="ml-4 space-y-0.5 border-l border-border/40 pl-2">
										{list.map((sub) => (
											<li key={sub.id}>
												<Link
													href={`/feed?sub=${encodeURIComponent(sub.id)}`}
													className={cn(
														"block truncate rounded px-2 py-1 text-sm",
														currentSub === sub.id
															? "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
															: "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
													)}
													title={sub.source_name}
													aria-current={currentSub === sub.id ? "page" : undefined}
												>
													{sub.source_name || sub.source_value || "未命名"}
												</Link>
											</li>
										))}
									</ul>
								</div>
							);
						})}
					</>
				) : null}
			</nav>

			<div className="border-t border-border/40 p-3">
				<div className="flex flex-col gap-0.5">
					<Link
						href="/subscriptions"
						className={cn(
							"flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200 motion-reduce:transition-none",
							pathname.startsWith("/subscriptions")
								? "bg-sidebar-accent text-sidebar-accent-foreground"
								: "text-sidebar-foreground/90 hover:bg-sidebar-accent/70 hover:text-sidebar-accent-foreground",
						)}
						aria-current={pathname.startsWith("/subscriptions") ? "page" : undefined}
					>
						<Plus className="size-4 shrink-0 opacity-80" aria-hidden />
						<span className={collapsed ? "sr-only" : undefined}>+ 添加订阅</span>
					</Link>
					<Link
						href="/settings"
						className={cn(
							"flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200 motion-reduce:transition-none",
							pathname.startsWith("/settings")
								? "bg-sidebar-accent text-sidebar-accent-foreground"
								: "text-sidebar-foreground/90 hover:bg-sidebar-accent/70 hover:text-sidebar-accent-foreground",
						)}
						aria-current={pathname.startsWith("/settings") ? "page" : undefined}
					>
						<Settings className="size-4 shrink-0 opacity-80" aria-hidden />
						<span className={collapsed ? "sr-only" : undefined}>设置</span>
					</Link>
					<Separator className="my-2" />
					<div className={cn("flex items-center px-2 py-1", collapsed ? "justify-center" : "justify-between")}>
						{!collapsed ? <span className="text-xs text-muted-foreground">主题</span> : null}
						<ThemeToggle />
					</div>
					{!collapsed ? (
						<a
							href={apiHealthUrl}
							target="_blank"
							rel="noreferrer"
							className="api-health-chip api-health-chip-sidebar mt-1 flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs"
							aria-live="polite"
						>
							<span className={`api-health-dot api-health-dot-${apiHealthState}`} aria-hidden />
								<span className="text-muted-foreground">API 状态：{apiHealthLabel}</span>
							</a>
						) : null}
					</div>
			</div>
		</>
	);
}

export function Sidebar({
	subscriptions,
	subscriptionsLoadError = false,
	apiHealthState,
	apiHealthUrl,
	apiHealthLabel,
}: SidebarProps) {
	const [collapsed, setCollapsed] = useState(false);

	useEffect(() => {
		if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
			return;
		}
		const mediaQuery = window.matchMedia("(max-width: 768px)");
		const syncCollapsed = () => {
			setCollapsed(mediaQuery.matches);
		};
		syncCollapsed();
		mediaQuery.addEventListener("change", syncCollapsed);
		return () => {
			mediaQuery.removeEventListener("change", syncCollapsed);
		};
	}, []);

	return (
		<aside
			className={cn(
				"flex shrink-0 flex-col border-r border-border/40 bg-background transition-[width] duration-200 motion-reduce:transition-none",
				collapsed ? "w-[72px]" : "w-[240px]"
			)}
			aria-label="侧边栏导航"
		>
			<div className="flex items-center justify-between border-b border-border/40 px-3 py-3">
				{collapsed ? (
						<Sheet>
							<SheetTrigger asChild>
								<Button variant="ghost" size="icon" aria-label="展开导航面板">
									<Menu className="size-4" />
								</Button>
							</SheetTrigger>
							<SheetContent side="left" className="w-[280px] p-0">
								<SheetTitle className="sr-only">移动端导航</SheetTitle>
								<SheetDescription className="sr-only">
									在移动端查看页面导航、订阅分组和全局状态入口。
								</SheetDescription>
								<aside aria-label="侧边栏导航" className="flex h-full flex-col bg-background">
									<ScrollArea className="flex-1">
				<SidebarNavContent
					collapsed={false}
					subscriptions={subscriptions}
					subscriptionsLoadError={subscriptionsLoadError}
					apiHealthState={apiHealthState}
					apiHealthUrl={apiHealthUrl}
					apiHealthLabel={apiHealthLabel}
										/>
									</ScrollArea>
								</aside>
							</SheetContent>
						</Sheet>
				) : (
					<span className="text-sm font-semibold tracking-tight text-foreground">导航</span>
				)}
				<Button
					type="button"
					variant="ghost"
					size="icon"
					aria-label={collapsed ? "展开侧边栏" : "折叠侧边栏"}
					onClick={() => setCollapsed((value) => !value)}
				>
					<PanelLeftClose className={cn("size-4 transition-transform motion-reduce:transition-none", collapsed && "rotate-180")} />
				</Button>
			</div>
			<ScrollArea className="flex-1">
				<SidebarNavContent
					collapsed={collapsed}
					subscriptions={subscriptions}
					subscriptionsLoadError={subscriptionsLoadError}
					apiHealthState={apiHealthState}
					apiHealthUrl={apiHealthUrl}
					apiHealthLabel={apiHealthLabel}
				/>
			</ScrollArea>
		</aside>
	);
}
