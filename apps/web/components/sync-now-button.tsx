"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { apiClient } from "@/lib/api/client";

const SYNC_FEEDBACK = {
	idle: {
		buttonLabel: "立即同步",
		badgeLabel: "待命",
		statusLabel: "待命：点击后立即同步最新内容。",
		liveMode: "polite" as const,
		statusClass: "status-chip status-pending",
	},
	loading: {
		buttonLabel: "同步中…",
		badgeLabel: "同步中",
		statusLabel: "正在拉取与分析新内容，请稍候。",
		liveMode: "polite" as const,
		statusClass: "status-chip status-running",
	},
	done: {
		buttonLabel: "同步完成",
		badgeLabel: "已完成",
		statusLabel: "同步完成，列表即将刷新。",
		liveMode: "polite" as const,
		statusClass: "status-chip status-succeeded",
	},
	error: {
		buttonLabel: "同步失败，重试",
		badgeLabel: "需重试",
		statusLabel: "同步失败，请检查网络后重试。",
		liveMode: "assertive" as const,
		statusClass: "status-chip status-failed",
	},
};

export function SyncNowButton() {
	const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");
	const router = useRouter();
	const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const isLoading = state === "loading";
	const feedback = SYNC_FEEDBACK[state];
	const stateFeedbackClass =
		state === "loading"
			? "btn-feedback-pending"
			: state === "done"
				? "btn-feedback-success"
				: state === "error"
					? "btn-feedback-error"
					: "";
	const statusChipFeedbackClass = state === "done" || state === "error" ? "status-chip-feedback" : "";

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

	async function handleSync() {
		setState("loading");
		clearTimer();
		try {
			await apiClient.pollIngest({});
			setState("done");
			timerRef.current = setTimeout(() => {
				setState("idle");
				router.refresh();
			}, 1500);
		} catch {
			setState("error");
		}
	}

	return (
		<>
			<button
				type="button"
				onClick={handleSync}
				disabled={isLoading}
				className={`${state === "error" ? "destructive" : "primary"} sync-now-button sync-now-button--${state} card-interactive ${stateFeedbackClass}`.trim()}
				aria-describedby="sync-now-status"
				aria-disabled={isLoading ? "true" : "false"}
				aria-busy={isLoading ? "true" : "false"}
				data-state={state}
				data-feedback-state={state}
				data-interaction="cta"
				title={state === "error" ? "同步失败，按 Enter 或空格可再次尝试。" : undefined}
			>
				<span className="inline" data-part="button-content" data-state={state}>
					<span className={feedback.statusClass} data-part="state-badge" data-state={state} aria-hidden="true">
						{feedback.badgeLabel}
					</span>
					<span data-part="button-label" data-state={state}>
						{feedback.buttonLabel}
					</span>
					{isLoading ? (
						<span className="sr-only" aria-hidden="true">
							正在同步，请稍候。
						</span>
					) : null}
				</span>
			</button>
			<span
				className={`small ${feedback.statusClass} ${statusChipFeedbackClass}`.trim()}
				data-part="status-hint"
				data-state={state}
				data-feedback-state={state}
				aria-hidden="true"
			>
				{feedback.statusLabel}
			</span>
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
				{feedback.statusLabel}
			</output>
		</>
	);
}
