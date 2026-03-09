"use client";

import { ErrorStateCard } from "@/components/error-state-card";

type RouteErrorProps = {
	error: Error & { digest?: string };
	reset: () => void;
};

export default function RouteError({ error, reset }: RouteErrorProps) {
	return (
		<section className="error-boundary-panel mx-auto flex min-h-[55vh] w-full max-w-xl items-center px-4 py-10">
			<ErrorStateCard
				eyebrow="页面异常"
				title="页面加载失败"
				titleAs="h2"
				description="出现了意外错误，请稍后重试或刷新页面。"
				digest={error.digest}
				onRetry={reset}
			/>
		</section>
	);
}
