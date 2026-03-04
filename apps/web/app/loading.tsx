export default function AppLoading() {
	return (
		<section className="card stack" aria-busy="true" aria-describedby="app-loading-message">
			<h2 className="skeleton-title" aria-hidden="true">
				页面加载中
			</h2>
			<div className="skeleton-block" aria-hidden="true">
				<div className="skeleton-line skeleton-line--long" />
				<div className="skeleton-line skeleton-line--medium" />
				<div className="skeleton-line skeleton-line--short" />
			</div>
			<p id="app-loading-message" role="status" aria-live="polite" aria-atomic="true">
				正在加载首页内容，请稍候。
			</p>
		</section>
	);
}
