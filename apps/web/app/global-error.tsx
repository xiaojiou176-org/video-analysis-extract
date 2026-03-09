"use client";

import { ErrorStateCard } from "@/components/error-state-card";

type GlobalErrorProps = {
	error: Error & { digest?: string };
	reset: () => void;
};

export default function GlobalError({ error, reset }: GlobalErrorProps) {
	return (
		<html lang="zh-Hans">
			<body className="min-h-screen bg-background text-foreground">
				<main className="global-error-shell mx-auto flex min-h-screen w-full max-w-xl items-center px-4 py-10">
					<ErrorStateCard
						eyebrow="系统异常"
						title="应用发生错误"
						titleAs="h1"
						description="出现系统异常，请稍后重试或刷新页面。"
						digest={error.digest}
						onRetry={reset}
						className="folo-surface w-full border-destructive/35 bg-destructive/5"
					/>
				</main>
			</body>
		</html>
	);
}
