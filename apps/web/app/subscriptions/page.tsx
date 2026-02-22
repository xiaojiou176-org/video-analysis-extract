import { deleteSubscriptionAction, upsertSubscriptionAction } from "@/app/subscriptions/actions";
import { apiClient } from "@/lib/api/client";
import { formatDateTime } from "@/lib/format";
import { resolveSearchParams, type SearchParamsInput } from "@/lib/search-params";

type SubscriptionsPageProps = {
  searchParams?: SearchParamsInput;
};

function renderAlert(status: string, message: string) {
  if (!status || !message) {
    return null;
  }
  const className = status === "error" ? "alert error" : "alert success";
  return <p className={className}>{message}</p>;
}

export default async function SubscriptionsPage({ searchParams }: SubscriptionsPageProps) {
  const { status, message } = await resolveSearchParams(searchParams, ["status", "message"] as const);
  const subscriptions = await apiClient.listSubscriptions().catch(() => []);

  return (
    <div className="stack">
      {renderAlert(status, message)}

      <section className="card stack">
        <h2>Create or update subscription</h2>
        <form action={upsertSubscriptionAction} className="grid grid-cols-2">
          <label>
            Platform
            <select name="platform" defaultValue="youtube">
              <option value="youtube">youtube</option>
              <option value="bilibili">bilibili</option>
            </select>
          </label>

          <label>
            Source type
            <select name="source_type" defaultValue="url">
              <option value="url">url</option>
              <option value="youtube_channel_id">youtube_channel_id</option>
              <option value="bilibili_uid">bilibili_uid</option>
            </select>
          </label>

          <label>
            Source value
            <input name="source_value" required placeholder="channel id / uid / url" />
          </label>

          <label>
            RSSHub route (optional)
            <input name="rsshub_route" placeholder="/youtube/channel/UCxxxx" />
          </label>

          <label className="inline">
            <input name="enabled" type="checkbox" defaultChecked />
            Enabled
          </label>

          <div className="inline">
            <button type="submit" className="primary">
              Save subscription
            </button>
          </div>
        </form>
      </section>

      <section className="card stack">
        <h2>Current subscriptions</h2>
        {subscriptions.length === 0 ? (
          <p className="small">No subscription data.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>Platform</th>
                <th>Type</th>
                <th>Enabled</th>
                <th>Updated</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {subscriptions.map((item) => (
                <tr key={item.id}>
                  <td>
                    <div>{item.source_value}</div>
                    <div className="small">{item.rsshub_route}</div>
                  </td>
                  <td>{item.platform}</td>
                  <td>{item.source_type}</td>
                  <td>{item.enabled ? "yes" : "no"}</td>
                  <td>{formatDateTime(item.updated_at)}</td>
                  <td>
                    <form action={deleteSubscriptionAction}>
                      <input type="hidden" name="id" value={item.id} />
                      <button type="submit" className="destructive">
                        Delete
                      </button>
                    </form>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
