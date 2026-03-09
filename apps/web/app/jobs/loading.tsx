import { LoadingStateCard } from "@/components/loading-state-card";

export default function JobsLoading() {
	return <LoadingStateCard title="任务页面加载中" message="正在加载任务信息，请稍候。" messageId="jobs-loading-message" />;
}
