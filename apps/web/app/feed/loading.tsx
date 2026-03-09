import { LoadingStateCard } from "@/components/loading-state-card";

export default function FeedLoading() {
	return <LoadingStateCard title="AI 摘要加载中" message="正在加载摘要流，请稍候。" messageId="feed-loading-message" />;
}
