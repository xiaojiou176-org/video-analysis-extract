import { LoadingStateCard } from "@/components/loading-state-card";

export default function SettingsLoading() {
	return <LoadingStateCard title="设置加载中" message="正在加载设置项，请稍候。" messageId="settings-loading-message" />;
}
