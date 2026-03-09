import { LoadingStateCard } from "@/components/loading-state-card";

export default function SubscriptionsLoading() {
	return (
		<LoadingStateCard
			title="订阅管理加载中"
			message="正在加载订阅数据，请稍候。"
			messageId="subscriptions-loading-message"
		/>
	);
}
