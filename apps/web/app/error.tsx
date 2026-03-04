"use client";

type RouteErrorProps = {
	error: Error & { digest?: string };
	reset: () => void;
};

export default function RouteError({ error, reset }: RouteErrorProps) {
	return (
		<section className="error-boundary-panel">
			<p className="error-boundary-eyebrow">页面异常</p>
			<h2 className="error-boundary-title">页面加载失败</h2>
			<p className="error-boundary-description" role="alert" aria-live="assertive" aria-atomic="true">
				出现了意外错误，请稍后重试或刷新页面。
			</p>
			{error.digest ? (
				<p className="error-boundary-meta">
					错误编号：<code>{error.digest}</code>
				</p>
			) : null}
			<button type="button" className="primary" onClick={reset}>
				重试页面
			</button>
		</section>
	);
}
