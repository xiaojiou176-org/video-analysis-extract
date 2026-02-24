export type DisplayStatus = {
  css: string;
  label: string;
};

const LABEL_MAP: Record<string, string> = {
  running: "运行中",
  queued: "排队中",
  succeeded: "已完成",
  failed: "已失败",
  degraded: "已降级",
  pending: "等待中",
  cancelled: "已取消",
  skipped: "已跳过",
};

export function toDisplayStatus(rawStatus: string | null | undefined): DisplayStatus {
  const normalized = (rawStatus ?? "").trim().toLowerCase();
  if (!normalized) {
    return { css: "queued", label: "-" };
  }
  return { css: normalized, label: LABEL_MAP[normalized] ?? normalized };
}
