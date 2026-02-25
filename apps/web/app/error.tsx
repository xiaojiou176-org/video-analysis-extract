"use client";

type RouteErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function RouteError({ error, reset }: RouteErrorProps) {
  return (
    <section className="error-boundary-panel" role="alert" aria-live="assertive" aria-atomic="true">
      <p className="error-boundary-eyebrow">页面异常</p>
      <h2 className="error-boundary-title">页面加载失败</h2>
      <p className="error-boundary-description">出现了意外错误，请重试。</p>
      {error.digest ? (
        <p className="error-boundary-meta">
          错误编号：<code>{error.digest}</code>
        </p>
      ) : null}
      <button type="button" className="primary" onClick={reset}>
        重试
      </button>
    </section>
  );
}
