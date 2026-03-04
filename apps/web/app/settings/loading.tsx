export default function SettingsLoading() {
	return (
		<section className="card stack" aria-busy="true" aria-describedby="settings-loading-message">
			<h2 className="skeleton-title" aria-hidden="true">
				设置加载中
			</h2>
			<div className="skeleton-block" aria-hidden="true">
				<div className="skeleton-line skeleton-line--long" />
				<div className="skeleton-line skeleton-line--medium" />
				<div className="skeleton-line skeleton-line--short" />
			</div>
			<p id="settings-loading-message" role="status" aria-live="polite" aria-atomic="true">
				正在加载设置项，请稍候。
			</p>
		</section>
	);
}
