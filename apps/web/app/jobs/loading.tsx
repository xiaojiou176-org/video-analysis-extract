export default function JobsLoading() {
	return (
		<section className="card stack" aria-busy="true" aria-describedby="jobs-loading-message">
			<h2 className="skeleton-title" aria-hidden="true">
				任务页面加载中
			</h2>
			<div className="skeleton-block" aria-hidden="true">
				<div className="skeleton-line skeleton-line--long" />
				<div className="skeleton-line skeleton-line--medium" />
				<div className="skeleton-line skeleton-line--short" />
			</div>
			<p id="jobs-loading-message" role="status" aria-live="polite" aria-atomic="true">
				正在加载任务信息，请稍候。
			</p>
		</section>
	);
}
