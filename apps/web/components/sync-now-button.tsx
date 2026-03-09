"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api/client";
import { cn } from "@/lib/utils";

const SYNC_FEEDBACK = {
	idle: {
		buttonLabel: "立即同步",
		badgeLabel: "待命",
		statusLabel: "待命：点击后立即同步最新内容。",
		liveMode: "polite" as const,
		badgeVariant: "outline" as const,
	},
	loading: {
		buttonLabel: "同步中…",
		badgeLabel: "同步中",
		statusLabel: "正在拉取与分析新内容，请稍候。",
		liveMode: "polite" as const,
		badgeVariant: "secondary" as const,
	},
	done: {
		buttonLabel: "同步完成",
		badgeLabel: "已完成",
		statusLabel: "同步完成，列表即将刷新。",
		liveMode: "polite" as const,
		badgeVariant: "secondary" as const,
	},
	error: {
		buttonLabel: "同步失败，重试",
		badgeLabel: "需重试",
		statusLabel: "同步失败，请检查网络后重试。",
		liveMode: "assertive" as const,
		badgeVariant: "destructive" as const,
	},
};

type SyncNowButtonProps = {
	sessionToken?: string;
};

export function SyncNowButton({ sessionToken }: SyncNowButtonProps) {
	const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");
	const router = useRouter();
	const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const isLoading = state === "loading";
	const feedback = SYNC_FEEDBACK[state];
	const buttonVariant =
		state === "loading" ? "secondary" : state === "done" ? "success" : state === "error" ? "destructive" : "hero";
	const liveStatusLabel =
		state === "loading"
			? "正在同步，请稍候。"
			: state === "done"
				? "同步完成，列表正在刷新。"
				: state === "error"
						? "同步失败，请检查网络后重试。"
						: "";
	const hintClassName = cn(
		"text-xs leading-5 text-muted-foreground transition-colors duration-200",
		state === "loading" && "text-amber-700 dark:text-amber-300",
		state === "done" && "text-emerald-700 dark:text-emerald-300",
		state === "error" && "text-destructive",
	);
	const clearTimer = useCallback(() => {
		if (!timerRef.current) {
			return;
		}
		clearTimeout(timerRef.current);
		timerRef.current = null;
	}, []);

	useEffect(() => {
		return () => {
			clearTimer();
		};
	}, [clearTimer]);

	function handleSync() {
		setState("loading");
		clearTimer();
		const request = sessionToken
			? apiClient.pollIngest({}, { webSessionToken: sessionToken })
			: apiClient.pollIngest({});
		request
			.then(() => {
				timerRef.current = setTimeout(() => {
					setState("done");
					timerRef.current = setTimeout(() => {
						setState("idle");
						router.refresh();
					}, 1500);
				}, 0);
			})
			.catch(() => {
				setState("error");
			});
	}

	return (
		<>
				<Button
					type="button"
					onClick={handleSync}
					disabled={isLoading}
					variant={buttonVariant}
					className={cn("min-w-[13rem] justify-between rounded-xl", !isLoading && "card-interactive")}
				aria-describedby="sync-now-status"
				aria-disabled={isLoading}
				aria-busy={isLoading}
				data-state={state}
				data-feedback-state={state}
				data-interaction="cta"
				title={state === "error" ? "同步失败，按 Enter 或空格可再次尝试。" : undefined}
			>
				<span className="inline-flex items-center gap-2" data-part="button-content" data-state={state}>
					<Badge
						variant={feedback.badgeVariant}
						className="rounded-full px-1.5 py-0 text-[10px] font-semibold"
						data-part="state-badge"
						data-state={state}
						aria-hidden="true"
					>
						{feedback.badgeLabel}
					</Badge>
					<span data-part="button-label" data-state={state}>
						{feedback.buttonLabel}
					</span>
					{isLoading ? (
						<span className="sr-only" aria-hidden="true">
							正在同步，请稍候。
						</span>
					) : null}
					</span>
				</Button>
				<p
					className={hintClassName}
					data-part="status-hint"
					data-state={state}
					data-feedback-state={state}
					aria-hidden="true"
				>
					{feedback.statusLabel}
				</p>
				<output
					id="sync-now-status"
					className="sr-only"
				role={state === "error" ? "alert" : "status"}
					aria-live={feedback.liveMode}
					aria-atomic="true"
					data-part="status-live"
					data-state={state}
					data-feedback-state={state}
				>
					{liveStatusLabel}
				</output>
			</>
	);
}
