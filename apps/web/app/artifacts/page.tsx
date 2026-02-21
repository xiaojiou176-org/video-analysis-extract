import { MarkdownPreview } from "@/components/markdown-preview";
import { apiClient } from "@/lib/api/client";

type ArtifactsPageProps = {
  searchParams?: {
    job_id?: string;
    video_url?: string;
  };
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

export default async function ArtifactsPage({ searchParams }: ArtifactsPageProps) {
  const jobId = searchParams?.job_id?.trim() ?? "";
  const videoUrl = searchParams?.video_url?.trim() ?? "";

  let error: string | null = null;
  const payload =
    jobId || videoUrl
      ? await apiClient
          .getArtifactMarkdown({
            job_id: jobId || undefined,
            video_url: videoUrl || undefined,
            include_meta: true,
          })
          .catch((err) => {
            error = err instanceof Error ? err.message : "Failed to load artifact";
            return null;
          })
      : null;

  const screenshotIndex = payload ? extractFrameFiles(payload.meta) : [];

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
            <h3>Screenshot index</h3>
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
      ) : (
        <p className="small">No artifact loaded yet.</p>
      )}
    </div>
  );
}
