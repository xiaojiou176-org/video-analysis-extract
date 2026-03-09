import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import FeedLoading from "@/app/feed/loading";
import JobsLoading from "@/app/jobs/loading";
import AppLoading from "@/app/loading";
import SettingsLoading from "@/app/settings/loading";
import SubscriptionsLoading from "@/app/subscriptions/loading";

type LoadingCase = {
	name: string;
	Component: () => JSX.Element;
	heading: string;
	message: string;
	describedBy: string;
};

const LOADING_CASES: LoadingCase[] = [
	{
		name: "dashboard loading",
		Component: AppLoading,
		heading: "页面加载中",
		message: "正在加载首页内容，请稍候。",
		describedBy: "app-loading-message",
	},
	{
		name: "jobs loading",
		Component: JobsLoading,
		heading: "任务页面加载中",
		message: "正在加载任务信息，请稍候。",
		describedBy: "jobs-loading-message",
	},
	{
		name: "settings loading",
		Component: SettingsLoading,
		heading: "设置加载中",
		message: "正在加载设置项，请稍候。",
		describedBy: "settings-loading-message",
	},
	{
		name: "subscriptions loading",
		Component: SubscriptionsLoading,
		heading: "订阅管理加载中",
		message: "正在加载订阅数据，请稍候。",
		describedBy: "subscriptions-loading-message",
	},
	{
		name: "feed loading",
		Component: FeedLoading,
		heading: "AI 摘要加载中",
		message: "正在加载摘要流，请稍候。",
		describedBy: "feed-loading-message",
	},
];

describe("app loading surfaces", () => {
	it.each(LOADING_CASES)("renders $name with accessible busy/status semantics", ({
		Component,
		heading,
		message,
		describedBy,
	}) => {
		const { container, unmount } = render(<Component />);

		const section = container.querySelector("section");
		expect(section).not.toBeNull();
		expect(section).toHaveAttribute("aria-busy", "true");
		expect(section).toHaveAttribute("aria-describedby", describedBy);

		const headingNode = screen.getByText(heading);
		expect(headingNode).toHaveAttribute("aria-hidden", "true");
		expect(container.querySelectorAll(".skeleton-line")).toHaveLength(3);

		const status = screen.getByRole("status");
		expect(status).toHaveAttribute("id", describedBy);
		expect(status).toHaveAttribute("aria-live", "polite");
		expect(status).toHaveAttribute("aria-atomic", "true");
		expect(status).toHaveTextContent(message);

		unmount();
	});
});
