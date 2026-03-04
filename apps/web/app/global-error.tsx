"use client";

type GlobalErrorProps = {
	error: Error & { digest?: string };
	reset: () => void;
};

export default function GlobalError({ error, reset }: GlobalErrorProps) {
	return (
		<html lang="zh-Hans">
			<body>
				<main className="global-error-shell">
					<p className="error-boundary-eyebrow">系统异常</p>
					<h1 className="error-boundary-title">应用发生错误</h1>
					<p
						className="error-boundary-description"
						role="alert"
						aria-live="assertive"
						aria-atomic="true"
					>
						出现系统异常，请稍后重试或刷新页面。
					</p>
					{error.digest ? (
						<p className="error-boundary-meta">
							错误编号：<code>{error.digest}</code>
						</p>
					) : null}
					<button type="button" className="primary" onClick={reset}>
						重试页面
					</button>
				</main>
			</body>
		</html>
	);
}
