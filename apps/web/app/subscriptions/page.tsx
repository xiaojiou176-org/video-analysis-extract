import { upsertSubscriptionAction } from "@/app/subscriptions/actions";
import { SubscriptionBatchPanel } from "@/components/subscription-batch-panel";
import { apiClient } from "@/lib/api/client";
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
            Adapter type
            <select name="adapter_type" defaultValue="rsshub_route">
              <option value="rsshub_route">rsshub_route</option>
              <option value="rss_generic">rss_generic</option>
            </select>
          </label>

          <label>
            Source URL (for rss_generic)
            <input name="source_url" placeholder="https://example.com/feed.xml" />
          </label>

          <label>
            RSSHub route (optional)
            <input name="rsshub_route" placeholder="/youtube/channel/UCxxxx" />
          </label>

          <label>
            Category
            <select name="category" defaultValue="misc">
              <option value="misc">misc</option>
              <option value="tech">tech</option>
              <option value="creator">creator</option>
              <option value="macro">macro</option>
              <option value="ops">ops</option>
            </select>
          </label>

          <label>
            Tags (comma separated, optional)
            <input name="tags" placeholder="ai,weekly,high-priority" />
          </label>
          <label>
            Priority (0-100)
            <input name="priority" type="number" min={0} max={100} defaultValue={50} />
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
        <p className="small">
          Select multiple rows to batch-update their category. Use the sticky action bar that appears at the bottom.
        </p>
        <SubscriptionBatchPanel subscriptions={subscriptions} />
      </section>
    </div>
  );
}
