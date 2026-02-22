import Link from "next/link";

import { toDisplayStatus } from "@/app/status";
import { apiClient } from "@/lib/api/client";
import { buildArtifactAssetUrl } from "@/lib/api/url";
import { formatDateTime, formatDateTimeWithSeconds } from "@/lib/format";
import { resolveSearchParams, type SearchParamsInput } from "@/lib/search-params";

type JobsPageProps = { searchParams?: SearchParamsInput };

export default async function JobsPage({ searchParams }: JobsPageProps) {
  const { job_id: jobId } = await resolveSearchParams(searchParams, ["job_id"] as const);

  let error: string | null = null;
  const job = jobId
    ? await apiClient
        .getJob(jobId)
        .catch((err) => {
          error = err instanceof Error ? err.message : "Failed to load job";
          return null;
        })
    : null;
  const jobStatus = job ? toDisplayStatus(job.status) : null;
  const pipelineStatus = job?.pipeline_final_status ? toDisplayStatus(job.pipeline_final_status) : null;

  return (
    <div className="stack">
      <section className="card stack">
        <h2>Job lookup</h2>
        <p className="small">Enter a Job ID to inspect step details and artifacts.</p>
        <form method="GET" className="inline" data-auto-disable-required="true">
          <label className="wide-field">
            Job ID *
            <input
              name="job_id"
              type="text"
              placeholder="9be4cbe7-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              defaultValue={jobId}
              required
              data-field-kind="identifier"
            />
          </label>
          <button type="submit" className="primary">
            Fetch job
          </button>
        </form>
      </section>

      {error ? <p className="alert error">{error}</p> : null}

      {job ? (
        <>
          <section className="card stack">
            <h2>Job summary</h2>
            <div className="grid grid-cols-2">
              <div>
                <div className="small">Job ID</div>
                <div>{job.id}</div>
              </div>
              <div>
                <div className="small">Video ID</div>
                <div>{job.video_id}</div>
              </div>
              <div>
                <div className="small">Status</div>
                <span className={`status-chip status-${jobStatus?.css ?? "queued"}`}>{jobStatus?.label ?? "-"}</span>
              </div>
              <div>
                <div className="small">Pipeline final</div>
                {pipelineStatus ? (
                  <span className={`status-chip status-${pipelineStatus.css}`}>{pipelineStatus.label}</span>
                ) : (
                  <div>-</div>
                )}
              </div>
              <div>
                <div className="small">Created</div>
                <div>{formatDateTime(job.created_at)}</div>
              </div>
              <div>
                <div className="small">Updated</div>
                <div>{formatDateTime(job.updated_at)}</div>
              </div>
            </div>
            <div className="inline">
              <Link href={`/artifacts?job_id=${job.id}`}>Open artifact page</Link>
            </div>
          </section>

          <section className="card stack">
            <h2>Step summary</h2>
            {job.step_summary.length === 0 ? (
              <p className="small">No step records found.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Step</th>
                    <th>Status</th>
                    <th>Attempt</th>
                    <th>Started</th>
                    <th>Finished</th>
                  </tr>
                </thead>
                <tbody>
                  {job.step_summary.map((step, index) => {
                    const stepStatus = toDisplayStatus(step.status);
                    return (
                      <tr key={`${step.name}-${index}`}>
                        <td>{step.name}</td>
                        <td>
                          <span className={`status-chip status-${stepStatus.css}`}>{stepStatus.label}</span>
                        </td>
                        <td>{step.attempt}</td>
                        <td>{formatDateTimeWithSeconds(step.started_at)}</td>
                        <td>{formatDateTimeWithSeconds(step.finished_at)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </section>

          <section className="grid grid-cols-2">
            <div className="card stack">
              <h3>Degradations</h3>
              {job.degradations.length === 0 ? (
                <p className="small">No degradations recorded.</p>
              ) : (
                <ul>
                  {job.degradations.map((item, index) => {
                    const degradationStatus =
                      typeof item.status === "string" ? toDisplayStatus(item.status).label : "n/a";
                    return (
                      <li key={`${item.step ?? "unknown"}-${index}`}>
                        <strong>{item.step ?? "unknown"}</strong>: {item.reason ?? degradationStatus}
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            <div className="card stack">
              <h3>Artifacts index</h3>
              {Object.keys(job.artifacts_index).length === 0 ? (
                <p className="small">No artifacts available.</p>
              ) : (
                <ul>
                  {Object.entries(job.artifacts_index).map(([key, value]) => (
                    <li key={key}>
                      <strong>{key}</strong>:{" "}
                      <a href={buildArtifactAssetUrl(job.id, value)} target="_blank" rel="noreferrer">
                        <code>{value}</code>
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
