"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { apiClient } from "@/lib/api/client";
import type { Platform, SourceType, SubscriptionAdapterType, SubscriptionCategory } from "@/lib/api/types";

function statusUrl(status: "success" | "error", message: string): string {
  const query = new URLSearchParams({ status, message });
  return `/subscriptions?${query.toString()}`;
}

export async function upsertSubscriptionAction(formData: FormData) {
  const platform = String(formData.get("platform") ?? "youtube").trim() as Platform;
  const sourceType = String(formData.get("source_type") ?? "url").trim() as SourceType;
  const sourceValue = String(formData.get("source_value") ?? "").trim();
  const adapterType = String(formData.get("adapter_type") ?? "rsshub_route").trim() as SubscriptionAdapterType;
  const sourceUrlRaw = String(formData.get("source_url") ?? "").trim();
  const rsshubRouteRaw = String(formData.get("rsshub_route") ?? "").trim();
  const category = String(formData.get("category") ?? "misc").trim() as SubscriptionCategory;
  const tagsRaw = String(formData.get("tags") ?? "").trim();
  const tags = tagsRaw
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
  const priorityRaw = String(formData.get("priority") ?? "50").trim();
  const parsedPriority = Number.parseInt(priorityRaw, 10);
  const priority = Number.isFinite(parsedPriority) ? Math.max(0, Math.min(100, parsedPriority)) : 50;
  const enabled = formData.get("enabled") === "on";

  if (!sourceValue) {
    redirect(statusUrl("error", "source_value is required"));
  }

  try {
    const result = await apiClient.upsertSubscription({
      platform,
      source_type: sourceType,
      source_value: sourceValue,
      adapter_type: adapterType,
      source_url: sourceUrlRaw || null,
      rsshub_route: rsshubRouteRaw || null,
      category,
      tags,
      priority,
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
