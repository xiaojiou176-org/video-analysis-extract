import Link from "next/link";

import { pollIngestAction, processVideoAction } from "@/app/actions";
import { toDisplayStatus } from "@/app/status";
import { apiClient } from "@/lib/api/client";
import { resolveSearchParams, type SearchParamsInput } from "@/lib/search-params";

type DashboardProps = {
  searchParams?: SearchParamsInput;
};

function renderAlert(status: string, message: string) {
  if (!status || !message) {
    return null;
  }

  const className = status === "error" ? "alert error" : "alert success";
  return <p className={className}>{message}</p>;
}

function toPlatformLabel(platform: string): string {
  const normalized = platform.trim().toLowerCase();
  if (normalized === "youtube") {
    return "YouTube";
  }
  if (normalized === "bilibili") {
    return "Bilibili";
  }
  return platform;
}

export default async function DashboardPage({ searchParams }: DashboardProps) {
  const { status, message } = await resolveSearchParams(searchParams, ["status", "message"] as const);
  const [subscriptions, videos] = await Promise.all([
    apiClient.listSubscriptions().catch(() => []),
    apiClient.listVideos({ limit: 200 }).catch(() => []),
  ]);

  const runningJobs = videos.filter((video) => video.status === "running" || video.status === "queued").length;
  const failedJobs = videos.filter((video) => video.status === "failed").length;

  return (
    <div className="stack">
      {renderAlert(status, message)}

      <section className="grid grid-cols-2">
        <div className="card metric">
          <span className="metric-label">Subscriptions</span>
          <span className="metric-value">{subscriptions.length}</span>
        </div>
        <div className="card metric">
          <span className="metric-label">Videos discovered</span>
          <span className="metric-value">{videos.length}</span>
        </div>
        <div className="card metric">
          <span className="metric-label">Running or queued</span>
          <span className="metric-value">{runningJobs}</span>
        </div>
        <div className="card metric">
          <span className="metric-label">Failed jobs</span>
          <span className="metric-value">{failedJobs}</span>
        </div>
      </section>

      <section className="grid grid-cols-2">
        <div className="card stack">
          <h2>Poll ingest</h2>
          <form action={pollIngestAction} className="stack form-fill">
            <label>
              Platform (optional)
              <select name="platform" defaultValue="">
                <option value="">All</option>
                <option value="youtube">YouTube</option>
                <option value="bilibili">Bilibili</option>
              </select>
            </label>

            <label>
              Max new videos
              <input name="max_new_videos" type="number" min={1} max={500} defaultValue={50} />
            </label>

            <div className="submit-row">
              <button className="primary" type="submit">
                Trigger ingest poll
              </button>
            </div>
          </form>
        </div>

        <div className="card stack">
          <h2>Process a video</h2>
          <form action={processVideoAction} className="stack form-fill" data-auto-disable-required="true">
            <label>
              Platform *
              <select name="platform" defaultValue="youtube">
                <option value="youtube">YouTube</option>
                <option value="bilibili">Bilibili</option>
              </select>
            </label>

            <label>
              Video URL *
              <input
                name="url"
                type="url"
                required
                placeholder="https://www.youtube.com/watch?v=..."
                data-field-kind="url"
              />
            </label>

            <label>
              Mode *
              <select name="mode" defaultValue="full">
                <option value="full">Full</option>
                <option value="text_only">Text Only</option>
                <option value="refresh_comments">Refresh Comments</option>
                <option value="refresh_llm">Refresh LLM</option>
              </select>
            </label>

            <div className="checkbox-row">
              <input id="force-run" name="force" type="checkbox" />
              <label htmlFor="force-run">Force run</label>
            </div>

            <div className="submit-row">
              <button className="primary" type="submit">
                Start processing
              </button>
            </div>
          </form>
        </div>
      </section>

      <section className="card stack">
        <h2>Recent videos</h2>
        {videos.length === 0 ? (
          <p className="small empty-state">No videos yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Title</th>
                <th>Platform</th>
                <th>Status</th>
                <th>Last Job</th>
              </tr>
            </thead>
            <tbody>
              {videos.slice(0, 10).map((video) => {
                const status = toDisplayStatus(video.status);
                return (
                  <tr key={video.id}>
                    <td>{video.title ?? video.video_uid}</td>
                    <td>{toPlatformLabel(video.platform)}</td>
                    <td>
                      <span className={`status-chip status-${status.css}`}>{status.label}</span>
                    </td>
                    <td>
                      {video.last_job_id ? (
                        <Link href={`/jobs?job_id=${video.last_job_id}`}>{video.last_job_id}</Link>
                      ) : (
                        "-"
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
