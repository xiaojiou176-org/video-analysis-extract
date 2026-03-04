export default function SubscriptionsLoading() {
	return (
		<section className="card stack" aria-busy="true" aria-describedby="subscriptions-loading-message">
			<h2 className="skeleton-title" aria-hidden="true">
				订阅管理加载中
			</h2>
			<div className="skeleton-block" aria-hidden="true">
				<div className="skeleton-line skeleton-line--long" />
				<div className="skeleton-line skeleton-line--medium" />
				<div className="skeleton-line skeleton-line--short" />
			</div>
			<p
				id="subscriptions-loading-message"
				role="status"
				aria-live="polite"
				aria-atomic="true"
			>
				正在加载订阅数据，请稍候。
			</p>
		</section>
	);
}
