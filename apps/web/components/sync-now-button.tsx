"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiClient } from "@/lib/api/client";

export function SyncNowButton() {
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");
  const router = useRouter();

  async function handleSync() {
    setState("loading");
    try {
      await apiClient.pollIngest({});
      setState("done");
      setTimeout(() => {
        setState("idle");
        router.refresh();
      }, 1500);
    } catch {
      setState("error");
      setTimeout(() => setState("idle"), 3000);
    }
  }

  const labels: Record<typeof state, string> = {
    idle: "Sync Now",
    loading: "Syncing…",
    done: "Done ✓",
    error: "Error — retry?",
  };

  return (
    <button
      type="button"
      onClick={handleSync}
      disabled={state === "loading"}
      className={state === "error" ? "destructive" : "primary"}
      style={{ minWidth: "7rem" }}
    >
      {labels[state]}
    </button>
  );
}
