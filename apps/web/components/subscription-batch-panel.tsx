"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiClient } from "@/lib/api/client";
import { formatDateTime } from "@/lib/format";
import type { Subscription, SubscriptionCategory } from "@/lib/api/types";

const CATEGORIES: SubscriptionCategory[] = ["tech", "creator", "macro", "ops", "misc"];

type Props = {
  subscriptions: Subscription[];
};

export function SubscriptionBatchPanel({ subscriptions }: Props) {
  const router = useRouter();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [batchCategory, setBatchCategory] = useState<SubscriptionCategory>("misc");
  const [applying, setApplying] = useState(false);
  const [applyResult, setApplyResult] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  function toggleAll() {
    if (selected.size === subscriptions.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(subscriptions.map((s) => s.id)));
    }
  }

  function toggleOne(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  async function handleDelete(id: string) {
    setDeletingId(id);
    try {
      await apiClient.deleteSubscription(id);
      setSelected((prev) => { const next = new Set(prev); next.delete(id); return next; });
      router.refresh();
    } catch (err) {
      setApplyResult(`删除失败：${err instanceof Error ? err.message : "未知错误"}`);
    } finally {
      setDeletingId(null);
    }
  }

  async function handleApplyCategory() {
    if (selected.size === 0) return;
    setApplying(true);
    setApplyResult(null);
    try {
      const result = await apiClient.batchUpdateSubscriptionCategory({
        ids: Array.from(selected),
        category: batchCategory,
      });
      setApplyResult(`已将 ${result.updated} 条订阅移至分类「${batchCategory}」`);
      setSelected(new Set());
      router.refresh();
    } catch (err) {
      setApplyResult(`操作失败：${err instanceof Error ? err.message : "未知错误"}`);
    } finally {
      setApplying(false);
    }
  }

  const allSelected = subscriptions.length > 0 && selected.size === subscriptions.length;

  return (
    <div className="stack">
      {subscriptions.length === 0 ? (
        <p className="small">暂无订阅数据。</p>
      ) : (
        <>
          <table>
            <thead>
              <tr>
                <th>
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleAll}
                    aria-label="全选"
                  />
                </th>
                <th>来源</th>
                <th>适配器</th>
                <th>平台</th>
                <th>类型</th>
                <th>分类</th>
                <th>优先级</th>
                <th>启用</th>
                <th>更新时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {subscriptions.map((item) => (
                <tr key={item.id}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selected.has(item.id)}
                      onChange={() => toggleOne(item.id)}
                      aria-label={`Select ${item.source_name}`}
                    />
                  </td>
                  <td>
                    <div>{item.source_name}</div>
                    <div className="small">UID/Value: {item.source_value}</div>
                    <div className="small">{item.rsshub_route}</div>
                  </td>
                  <td>
                    <div>{item.adapter_type}</div>
                    <div className="small">{item.source_url ?? "-"}</div>
                  </td>
                  <td>{item.platform}</td>
                  <td>{item.source_type}</td>
                  <td>
                    <div>{item.category}</div>
                    <div className="small">{item.tags.join(", ") || "-"}</div>
                  </td>
                  <td>{item.priority}</td>
                  <td>{item.enabled ? "是" : "否"}</td>
                  <td>{formatDateTime(item.updated_at)}</td>
                  <td>
                    <button
                      type="button"
                      className="destructive"
                      disabled={deletingId === item.id}
                      onClick={() => handleDelete(item.id)}
                    >
                      {deletingId === item.id ? "…" : "删除"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {selected.size > 0 && (
            <div
              className="card inline"
              style={{
                position: "sticky",
                bottom: "1rem",
                justifyContent: "space-between",
                alignItems: "center",
                background: "var(--color-surface, #fff)",
                boxShadow: "0 -2px 8px rgba(0,0,0,.12)",
              }}
            >
              <span className="small">
                已选 {selected.size} 条
              </span>
              <div className="inline">
                <label style={{ margin: 0 }}>
                  批量设分类
                  <select
                    value={batchCategory}
                    onChange={(e) => setBatchCategory(e.target.value as SubscriptionCategory)}
                  >
                    {CATEGORIES.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  className="primary"
                  disabled={applying}
                  onClick={handleApplyCategory}
                >
                  {applying ? "应用中…" : "应用"}
                </button>
                <button
                  type="button"
                  onClick={() => setSelected(new Set())}
                >
                  取消
                </button>
              </div>
            </div>
          )}

          {applyResult && (
            <p className={applyResult.startsWith("操作失败") || applyResult.startsWith("删除失败") ? "alert error" : "alert success"}>
              {applyResult}
            </p>
          )}
        </>
      )}
    </div>
  );
}
