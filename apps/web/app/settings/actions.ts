"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { apiClient } from "@/lib/api/client";

function statusUrl(status: "success" | "error", message: string): string {
  const query = new URLSearchParams({ status, message });
  return `/settings?${query.toString()}`;
}

function toOptionalString(value: FormDataEntryValue | null): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export async function updateNotificationConfigAction(formData: FormData) {
  const enabled = formData.get("enabled") === "on";
  const dailyDigestEnabled = formData.get("daily_digest_enabled") === "on";
  const failureAlertEnabled = formData.get("failure_alert_enabled") === "on";
  const toEmail = toOptionalString(formData.get("to_email"));
  const hourRaw = toOptionalString(formData.get("daily_digest_hour_utc"));

  let dailyDigestHourUtc: number | null = null;
  if (hourRaw !== null) {
    const parsed = Number.parseInt(hourRaw, 10);
    if (!Number.isFinite(parsed) || parsed < 0 || parsed > 23) {
      redirect(statusUrl("error", "daily_digest_hour_utc must be in [0, 23]"));
    }
    dailyDigestHourUtc = parsed;
  }

  try {
    await apiClient.updateNotificationConfig({
      enabled,
      to_email: toEmail,
      daily_digest_enabled: dailyDigestEnabled,
      daily_digest_hour_utc: dailyDigestHourUtc,
      failure_alert_enabled: failureAlertEnabled,
    });

    revalidatePath("/settings");
    redirect(statusUrl("success", "Notification config saved"));
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to update config";
    redirect(statusUrl("error", message));
  }
}

export async function sendTestNotificationAction(formData: FormData) {
  const toEmail = toOptionalString(formData.get("to_email"));
  const subject = toOptionalString(formData.get("subject"));
  const body = toOptionalString(formData.get("body"));

  try {
    const result = await apiClient.sendNotificationTest({
      to_email: toEmail,
      subject,
      body,
    });

    revalidatePath("/settings");
    redirect(statusUrl("success", `Test notification status: ${result.status}`));
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to send test notification";
    redirect(statusUrl("error", message));
  }
}
