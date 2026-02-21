import { MarkdownPreview } from "@/components/markdown-preview";
import { apiClient } from "@/lib/api/client";
import type { ArtifactMarkdownWithMeta } from "@/lib/api/types";
import { resolveSearchParams, type SearchParamsInput } from "@/lib/search-params";

type ArtifactsPageProps = {
  searchParams?: SearchParamsInput;
};

function getApiBaseUrl(): string {
  const base =
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    process.env.VD_API_BASE_URL ??
    "http://127.0.0.1:8000";
  return base.replace(/\/$/, "");
}

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
  if (lower.endsWith(".jpeg")) {
    return "image/jpeg";
  }
  return "image/jpeg";
}

function buildArtifactAssetUrl(jobId: string, path: string): string {
  const target = new URL("/api/v1/artifacts/assets", getApiBaseUrl());
  target.searchParams.set("job_id", jobId);
  target.searchParams.set("path", path);
  return target.toString();
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
        <h2>Artifact lookup</h2>
        <form method="GET" className="grid grid-cols-2">
          <label>
            Job ID
            <input name="job_id" type="text" defaultValue={jobId} placeholder="job uuid" />
          </label>

          <label>
            Video URL
            <input name="video_url" type="url" defaultValue={videoUrl} placeholder="https://..." />
          </label>

          <div className="inline">
            <button type="submit" className="primary">
              Load artifact markdown
            </button>
          </div>
        </form>
        <p className="small">Provide either job_id or video_url.</p>
      </section>

      {error ? <p className="alert error">{error}</p> : null}

      {payload ? (
        <>
          <section className="card stack">
            <h3>Embedded screenshots</h3>
            {embeddedScreenshots.length === 0 ? (
              <p className="small">No screenshots found in meta.frame_files.</p>
            ) : (
              <ol>
                {embeddedScreenshots.map((item, index) => (
                  <li key={`${item.path}-${index}`} className="stack">
                    {item.assetUrl ? (
                      <object
                        data={item.assetUrl}
                        type={item.mimeType}
                        style={{ width: "100%", minHeight: "120px", borderRadius: "8px" }}
                      >
                        <p className="small">
                          Unable to load screenshot, fallback path: <code>{item.path}</code>
                        </p>
                      </object>
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
            <h3>Screenshot index (fallback)</h3>
            {screenshotIndex.length === 0 ? (
              <p className="small">No screenshot paths found in meta.frame_files.</p>
            ) : (
              <ol>
                {screenshotIndex.map((path, index) => (
                  <li key={`${path}-${index}`}>
                    <code>{path}</code>
                  </li>
                ))}
              </ol>
            )}
          </section>

          <section className="card stack">
            <h3>Markdown preview</h3>
            <MarkdownPreview markdown={payload.markdown} />
          </section>
        </>
      ) : !hasLookupParams ? (
        <p className="small">No artifact loaded yet.</p>
      ) : !error ? (
        <p className="small">Artifact request completed but no markdown payload was returned.</p>
      ) : (
        <p className="small">Artifact request failed.</p>
      )}
    </div>
  );
}
