import Link from "next/link";

import { apiClient } from "@/lib/api/client";
import { formatDateTime } from "@/lib/format";

type JobsPageProps = {
  searchParams?: {
    job_id?: string;
  };
};

export default async function JobsPage({ searchParams }: JobsPageProps) {
  const jobId = searchParams?.job_id?.trim() ?? "";

  let error: string | null = null;
  const job = jobId
    ? await apiClient
        .getJob(jobId)
        .catch((err) => {
          error = err instanceof Error ? err.message : "Failed to load job";
          return null;
        })
    : null;

  return (
    <div className="stack">
      <section className="card stack">
        <h2>Job lookup</h2>
        <form method="GET" className="inline">
          <label style={{ minWidth: "420px", flex: 1 }}>
            Job ID
            <input
              name="job_id"
              type="text"
              placeholder="9be4cbe7-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              defaultValue={jobId}
            />
          </label>
          <button type="submit" className="primary">
            Fetch job
          </button>
        </form>
      </section>

      {!jobId ? <p className="small">Enter a job id to inspect step details and artifacts.</p> : null}

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
                <span className={`status-chip status-${job.status}`}>{job.status}</span>
              </div>
              <div>
                <div className="small">Pipeline final</div>
                <div>{job.pipeline_final_status ?? "-"}</div>
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
                  {job.step_summary.map((step, index) => (
                    <tr key={`${step.name}-${index}`}>
                      <td>{step.name}</td>
                      <td>{step.status}</td>
                      <td>{step.attempt}</td>
                      <td>{formatDateTime(step.started_at)}</td>
                      <td>{formatDateTime(step.finished_at)}</td>
                    </tr>
                  ))}
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
                  {job.degradations.map((item, index) => (
                    <li key={`${item.step ?? "unknown"}-${index}`}>
                      <strong>{item.step ?? "unknown"}</strong>: {item.reason ?? item.status ?? "n/a"}
                    </li>
                  ))}
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
                      <strong>{key}</strong>: <code>{value}</code>
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
