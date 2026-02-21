"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { apiClient } from "@/lib/api/client";
import type { Platform, VideoProcessRequest } from "@/lib/api/types";

function statusUrl(pathname: string, status: "success" | "error", message: string): string {
  const query = new URLSearchParams({ status, message });
  return `${pathname}?${query.toString()}`;
}

export async function pollIngestAction(formData: FormData) {
  const platformRaw = String(formData.get("platform") ?? "").trim();
  const maxNewVideosRaw = String(formData.get("max_new_videos") ?? "50").trim();
  const maxNewVideos = Number.parseInt(maxNewVideosRaw, 10);

  try {
    const result = await apiClient.pollIngest({
      platform: platformRaw ? (platformRaw as Platform) : undefined,
      max_new_videos: Number.isFinite(maxNewVideos) ? maxNewVideos : 50,
    });
    revalidatePath("/");
    revalidatePath("/jobs");
    redirect(statusUrl("/", "success", `Enqueued ${result.enqueued} new jobs`));
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to poll ingest";
    redirect(statusUrl("/", "error", message));
  }
}

export async function processVideoAction(formData: FormData) {
  const platform = String(formData.get("platform") ?? "youtube").trim() as Platform;
  const sourceUrl = String(formData.get("url") ?? "").trim();
  const mode = String(formData.get("mode") ?? "full").trim() as VideoProcessRequest["mode"];
  const force = formData.get("force") === "on";

  if (!sourceUrl) {
    redirect(statusUrl("/", "error", "Video URL is required"));
  }

  try {
    const result = await apiClient.processVideo({
      video: { platform, url: sourceUrl },
      mode,
      force,
    });

    revalidatePath("/");
    revalidatePath("/jobs");
    revalidatePath("/artifacts");
    redirect(statusUrl("/", "success", `Job created: ${result.job_id}`));
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to start process";
    redirect(statusUrl("/", "error", message));
  }
}
