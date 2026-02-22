import { sendTestNotificationAction, updateNotificationConfigAction } from "@/app/settings/actions";
import { apiClient } from "@/lib/api/client";
import { formatDateTime } from "@/lib/format";
import { resolveSearchParams, type SearchParamsInput } from "@/lib/search-params";

type SettingsPageProps = {
  searchParams?: SearchParamsInput;
};

export default async function SettingsPage({ searchParams }: SettingsPageProps) {
  const { status, message } = await resolveSearchParams(searchParams, ["status", "message"] as const);
  const configResult = await apiClient
    .getNotificationConfig()
    .then((config) => ({ config, error: null as string | null }))
    .catch((err) => ({
      config: null,
      error: err instanceof Error ? err.message : "Failed to load notification config",
    }));
  const { config, error: loadError } = configResult;

  const alert =
    status && message ? (
      <p className={status === "error" ? "alert error" : "alert success"}>{message}</p>
    ) : null;

  return (
    <div className="stack">
      {alert}
      {loadError ? <p className="alert error">{loadError}</p> : null}

      <section className="card stack">
        <h2>Notification config</h2>
        <form action={updateNotificationConfigAction} className="stack">
          <label className="inline">
            <input name="enabled" type="checkbox" defaultChecked={config?.enabled ?? true} />
            Enable notifications
          </label>

          <label>
            Recipient email
            <input
              name="to_email"
              type="email"
              defaultValue={config?.to_email ?? ""}
              placeholder="ops@example.com"
            />
          </label>

          <label className="inline">
            <input
              name="daily_digest_enabled"
              type="checkbox"
              defaultChecked={config?.daily_digest_enabled ?? false}
            />
            Enable daily digest
          </label>

          <label>
            Daily digest hour (UTC)
            <input
              name="daily_digest_hour_utc"
              type="number"
              min={0}
              max={23}
              defaultValue={config?.daily_digest_hour_utc ?? ""}
            />
          </label>

          <label className="inline">
            <input
              name="failure_alert_enabled"
              type="checkbox"
              defaultChecked={config?.failure_alert_enabled ?? true}
            />
            Enable failure alert
          </label>

          <button type="submit" className="primary">
            Save config
          </button>
        </form>

        {config ? (
          <p className="small">
            Created: {formatDateTime(config.created_at)} | Updated: {formatDateTime(config.updated_at)}
          </p>
        ) : null}
      </section>

      <section className="card stack">
        <h2>Send test notification</h2>
        <form action={sendTestNotificationAction} className="stack">
          <label>
            Override recipient (optional)
            <input name="to_email" type="email" placeholder="leave empty to use configured recipient" />
          </label>

          <label>
            Subject (optional)
            <input name="subject" type="text" placeholder="Video Digestor test notification" />
          </label>

          <label>
            Body (optional)
            <textarea name="body" rows={4} placeholder="This is a test notification from Video Digestor." />
          </label>

          <button type="submit" className="primary">
            Send test email
          </button>
        </form>
      </section>
    </div>
  );
}
