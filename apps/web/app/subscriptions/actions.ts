"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { apiClient } from "@/lib/api/client";
import type { Platform, SourceType } from "@/lib/api/types";

function statusUrl(status: "success" | "error", message: string): string {
  const query = new URLSearchParams({ status, message });
  return `/subscriptions?${query.toString()}`;
}

export async function upsertSubscriptionAction(formData: FormData) {
  const platform = String(formData.get("platform") ?? "youtube").trim() as Platform;
  const sourceType = String(formData.get("source_type") ?? "url").trim() as SourceType;
  const sourceValue = String(formData.get("source_value") ?? "").trim();
  const rsshubRouteRaw = String(formData.get("rsshub_route") ?? "").trim();
  const enabled = formData.get("enabled") === "on";

  if (!sourceValue) {
    redirect(statusUrl("error", "source_value is required"));
  }

  try {
    const result = await apiClient.upsertSubscription({
      platform,
      source_type: sourceType,
      source_value: sourceValue,
      rsshub_route: rsshubRouteRaw || null,
      enabled,
    });

    revalidatePath("/subscriptions");
    redirect(statusUrl("success", result.created ? "Subscription created" : "Subscription updated"));
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to save subscription";
    redirect(statusUrl("error", message));
  }
}

export async function deleteSubscriptionAction(formData: FormData) {
  const id = String(formData.get("id") ?? "").trim();
  if (!id) {
    redirect(statusUrl("error", "Missing subscription id"));
  }

  try {
    await apiClient.deleteSubscription(id);
    revalidatePath("/subscriptions");
    redirect(statusUrl("success", "Subscription deleted"));
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to delete subscription";
    redirect(statusUrl("error", message));
  }
}
