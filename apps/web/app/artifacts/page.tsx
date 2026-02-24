import { MarkdownPreview } from "@/components/markdown-preview";
import { apiClient } from "@/lib/api/client";
import { buildArtifactAssetUrl } from "@/lib/api/url";
import type { ArtifactMarkdownWithMeta } from "@/lib/api/types";
import { resolveSearchParams, type SearchParamsInput } from "@/lib/search-params";

type ArtifactsPageProps = {
  searchParams?: SearchParamsInput;
};

function extractFrameFiles(meta: Record<string, unknown> | null): string[] {
  if (!meta) {
    return [];
  }
  const frameFiles = meta.frame_files;
  if (!Array.isArray(frameFiles)) {
    return [];
  }
  return frameFiles.filter((item): item is string => typeof item === "string" && item.length > 0);
}

function extractArtifactJobId(jobId: string, meta: Record<string, unknown> | null): string {
  if (jobId) {
    return jobId;
  }
  if (!meta) {
    return "";
  }

  const job = meta.job;
  if (!job || typeof job !== "object") {
    return "";
  }

  const rawJobId = (job as Record<string, unknown>).id;
  return typeof rawJobId === "string" ? rawJobId : "";
}

function inferImageMime(path: string): string {
  const lower = path.toLowerCase();
  if (lower.endsWith(".png")) {
    return "image/png";
  }
  if (lower.endsWith(".webp")) {
    return "image/webp";
  }
  if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) {
    return "image/jpeg";
  }
  return "application/octet-stream";
}

export default async function ArtifactsPage({ searchParams }: ArtifactsPageProps) {
  const { job_id: jobId, video_url: videoUrl } = await resolveSearchParams(searchParams, [
    "job_id",
    "video_url",
  ] as const);
  const hasLookupParams = Boolean(jobId || videoUrl);

  let error: string | null = null;
  let payload: ArtifactMarkdownWithMeta | null = null;

  if (hasLookupParams) {
    payload = await apiClient
      .getArtifactMarkdown({
        job_id: jobId || undefined,
        video_url: videoUrl || undefined,
        include_meta: true,
      })
      .catch((err) => {
        const reason = err instanceof Error ? err.message : "Failed to load artifact";
        error = `API error: ${reason}`;
        return null;
      });
  }

  const screenshotIndex = payload ? extractFrameFiles(payload.meta) : [];
  const artifactJobId = payload ? extractArtifactJobId(jobId, payload.meta) : "";
  const embeddedScreenshots = screenshotIndex.map((path) => ({
    path,
    mimeType: inferImageMime(path),
    assetUrl: artifactJobId ? buildArtifactAssetUrl(artifactJobId, path) : null,
  }));

  return (
    <div className="stack">
      <section className="card stack">
        <h2>产物查询</h2>
        <p className="small">
          输入任务 ID 或视频 URL，加载对应的 Markdown 产物和截图。
        </p>
        <form method="GET" className="stack" data-require-one="job_id,video_url" data-require-one-exclusive="true">
          <label>
            任务 ID
            <input
              name="job_id"
              type="text"
              defaultValue={jobId}
              placeholder="9be4cbe7-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              data-field-kind="identifier"
            />
          </label>

          <p className="small artifacts-or-divider" aria-label="二选一">
            或
          </p>

          <label>
            视频 URL
            <input
              name="video_url"
              type="url"
              defaultValue={videoUrl}
              placeholder="https://www.youtube.com/watch?v=..."
              data-field-kind="url"
            />
          </label>

          <div>
            <button type="submit" className="primary">
              加载产物
            </button>
          </div>
        </form>
      </section>

      {error ? <p className="alert error">{error}</p> : null}

      {payload ? (
        <>
          <section className="card stack">
            <h3>内嵌截图</h3>
            {embeddedScreenshots.length === 0 ? (
              <p className="small">meta.frame_files 中未找到截图。</p>
            ) : (
              <ol>
                {embeddedScreenshots.map((item, index) => (
                  <li key={`${item.path}-${index}`} className="stack">
                    {item.assetUrl ? (
                      <>
                        <a className="screenshot-link" href={item.assetUrl} target="_blank" rel="noreferrer">
                          查看截图 {index + 1}
                        </a>
                        <object
                          aria-label={`Screenshot ${index + 1}: ${item.path}`}
                          data={item.assetUrl}
                          type={item.mimeType}
                          style={{
                            width: "100%",
                            minHeight: "120px",
                            maxHeight: "320px",
                            borderRadius: "8px",
                            border: "1px solid var(--color-border)",
                            background: "#f8fafc",
                          }}
                        >
                          <p className="small">
                            Unable to load screenshot, fallback path: <code>{item.path}</code>
                          </p>
                        </object>
                      </>
                    ) : (
                      <p className="small">
                        Missing job_id for screenshot preview, fallback path: <code>{item.path}</code>
                      </p>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </section>

          <section className="card stack">
            <h3>截图索引（备用链接）</h3>
            {screenshotIndex.length === 0 ? (
              <p className="small">meta.frame_files 中未找到截图路径。</p>
            ) : (
              <ol>
                {screenshotIndex.map((path, index) => (
                  <li key={`${path}-${index}`}>
                    {artifactJobId ? (
                      <a
                        className="screenshot-link"
                        href={buildArtifactAssetUrl(artifactJobId, path)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open <code>{path}</code>
                      </a>
                    ) : (
                      <code>{path}</code>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </section>

          <section className="card stack">
            <h3>Markdown 预览</h3>
            <MarkdownPreview markdown={payload.markdown} />
          </section>
        </>
      ) : !hasLookupParams ? (
        null
      ) : !error ? (
        <p className="small">产物请求已完成，但未返回 Markdown 内容。</p>
      ) : (
        null
      )}
    </div>
  );
}
