import type { Metadata } from "next";

import { upsertSubscriptionAction } from "@/app/subscriptions/actions";

export const metadata: Metadata = { title: "订阅管理" };
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
        <h2>创建或更新订阅</h2>
        <form action={upsertSubscriptionAction} className="grid grid-cols-2">
          <label>
            平台
            <select name="platform" defaultValue="youtube">
              <option value="youtube">youtube</option>
              <option value="bilibili">bilibili</option>
            </select>
          </label>

          <label>
            来源类型
            <select name="source_type" defaultValue="url">
              <option value="url">url</option>
              <option value="youtube_channel_id">youtube_channel_id</option>
              <option value="bilibili_uid">bilibili_uid</option>
            </select>
          </label>

          <label>
            来源值
            <input name="source_value" required placeholder="频道 ID / UID / URL" />
          </label>

          <label>
            适配器类型
            <select name="adapter_type" defaultValue="rsshub_route">
              <option value="rsshub_route">rsshub_route</option>
              <option value="rss_generic">rss_generic</option>
            </select>
          </label>

          <label>
            来源 URL（rss_generic 时使用）
            <input name="source_url" placeholder="https://example.com/feed.xml" />
          </label>

          <label>
            RSSHub 路由（可选）
            <input name="rsshub_route" placeholder="/youtube/channel/UCxxxx" />
          </label>

          <label>
            分类
            <select name="category" defaultValue="misc">
              <option value="misc">misc</option>
              <option value="tech">tech</option>
              <option value="creator">creator</option>
              <option value="macro">macro</option>
              <option value="ops">ops</option>
            </select>
          </label>

          <label>
            标签（逗号分隔，可选）
            <input name="tags" placeholder="ai,weekly,high-priority" />
          </label>
          <label>
            优先级 (0-100)
            <input name="priority" type="number" min={0} max={100} defaultValue={50} />
          </label>

          <label className="inline">
            <input name="enabled" type="checkbox" defaultChecked />
            启用
          </label>

          <div className="inline">
            <button type="submit" className="primary">
              保存订阅
            </button>
          </div>
        </form>
      </section>

      <section className="card stack">
        <h2>当前订阅列表</h2>
        <p className="small">
          勾选多行可批量更新分类，底部将出现操作栏。
        </p>
        <SubscriptionBatchPanel subscriptions={subscriptions} />
      </section>
    </div>
  );
}
