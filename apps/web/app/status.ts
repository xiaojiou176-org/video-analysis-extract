export type DisplayStatus = {
  css: string;
  label: string;
};

export function toDisplayStatus(rawStatus: string | null | undefined): DisplayStatus {
  const normalized = (rawStatus ?? "").trim().toLowerCase();
  if (!normalized) {
    return { css: "queued", label: "-" };
  }
  return { css: normalized, label: normalized };
}
