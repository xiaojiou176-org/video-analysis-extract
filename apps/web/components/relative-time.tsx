"use client";

import { useEffect, useState } from "react";

type Props = {
	dateTime: string;
};

function formatRelative(dateTime: string): string {
	const date = new Date(dateTime);
	if (Number.isNaN(date.getTime())) {
		return dateTime;
	}

	const diffMs = Date.now() - date.getTime();
	if (diffMs < 0) {
		const futureSec = Math.floor(Math.abs(diffMs) / 1000);
		const futureMin = Math.floor(futureSec / 60);
		const futureHour = Math.floor(futureMin / 60);
		const futureDay = Math.floor(futureHour / 24);

		if (futureSec < 60) {
			return "马上";
		}
		if (futureMin < 60) {
			return `${Math.max(1, futureMin)} 分钟后`;
		}
		if (futureHour < 24) {
			return `${Math.max(1, futureHour)} 小时后`;
		}
		if (futureDay < 2) {
			return "明天";
		}
		if (futureDay < 7) {
			return `${futureDay} 天后`;
		}
		if (futureDay < 30) {
			return `${Math.floor(futureDay / 7)} 周后`;
		}
		if (futureDay < 365) {
			return `${Math.floor(futureDay / 30)} 个月后`;
		}
		return `${Math.floor(futureDay / 365)} 年后`;
	}

	const diffSec = Math.floor(diffMs / 1000);
	const diffMin = Math.floor(diffSec / 60);
	const diffHour = Math.floor(diffMin / 60);
	const diffDay = Math.floor(diffHour / 24);

	if (diffSec < 60) {
		return "刚刚";
	}
	if (diffMin < 60) {
		return `${diffMin} 分钟前`;
	}
	if (diffHour < 24) {
		return `${diffHour} 小时前`;
	}
	if (diffDay < 7) {
		return `${diffDay} 天前`;
	}
	if (diffDay < 30) {
		return `${Math.floor(diffDay / 7)} 周前`;
	}
	if (diffDay < 365) {
		return `${Math.floor(diffDay / 30)} 个月前`;
	}
	return `${Math.floor(diffDay / 365)} 年前`;
}

function formatAbsolute(dateTime: string): string {
	const date = new Date(dateTime);
	if (Number.isNaN(date.getTime())) {
		return dateTime;
	}
	return date.toLocaleString("zh-CN", {
		year: "numeric",
		month: "2-digit",
		day: "2-digit",
		hour: "2-digit",
		minute: "2-digit",
	});
}

export function RelativeTime({ dateTime }: Props) {
	const [relative, setRelative] = useState<string>(() => formatRelative(dateTime));
	const absolute = formatAbsolute(dateTime);

	useEffect(() => {
		const timer = setInterval(() => setRelative(formatRelative(dateTime)), 60_000);
		return () => clearInterval(timer);
	}, [dateTime]);

	return (
		<time dateTime={dateTime} title={absolute} className="relative-time">
			{relative}
		</time>
	);
}
