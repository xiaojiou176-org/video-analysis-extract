"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { apiClient } from "@/lib/api/client";

export function SyncNowButton() {
	const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");
	const router = useRouter();
	const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

	function clearTimer() {
		if (!timerRef.current) {
			return;
		}
		clearTimeout(timerRef.current);
		timerRef.current = null;
	}

	useEffect(() => {
		return () => {
			clearTimer();
		};
	}, []);

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
			timerRef.current = setTimeout(() => setState("idle"), 3000);
		}
	}

	const labels: Record<typeof state, string> = {
		idle: "立即同步",
		loading: "同步中…",
		done: "完成 ✓",
		error: "出错，重试？",
	};

	return (
		<>
			<button
				type="button"
				onClick={handleSync}
				disabled={state === "loading"}
				className={state === "error" ? "destructive" : "primary"}
				style={{ minWidth: "7rem" }}
				aria-describedby="sync-now-status"
			>
				{labels[state]}
			</button>
			<output id="sync-now-status" className="sr-only" aria-live="polite">
				{labels[state]}
			</output>
		</>
	);
}
