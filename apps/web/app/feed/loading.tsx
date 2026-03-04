export default function FeedLoading() {
	return (
		<section className="card stack" aria-busy="true" aria-describedby="feed-loading-message">
			<h2 className="skeleton-title" aria-hidden="true">
				AI 摘要加载中
			</h2>
			<div className="skeleton-block" aria-hidden="true">
				<div className="skeleton-line skeleton-line--long" />
				<div className="skeleton-line skeleton-line--medium" />
				<div className="skeleton-line skeleton-line--short" />
			</div>
			<p id="feed-loading-message" role="status" aria-live="polite" aria-atomic="true">
				正在加载摘要流，请稍候。
			</p>
		</section>
	);
}
