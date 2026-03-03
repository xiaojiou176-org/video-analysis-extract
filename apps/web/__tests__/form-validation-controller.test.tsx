import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { usePathnameMock } = vi.hoisted(() => ({
	usePathnameMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
	usePathname: usePathnameMock,
}));

import { FormValidationController } from "@/components/form-validation-controller";

describe("FormValidationController", () => {
	beforeEach(() => {
		usePathnameMock.mockReturnValue("/");
	});

	it("disables submit until required fields are valid", () => {
		render(
			<>
				<FormValidationController />
				<form data-auto-disable-required="true">
					<input aria-label="name" name="name" required defaultValue="" />
					<button type="submit">提交</button>
				</form>
			</>,
		);

		const button = screen.getByRole("button", { name: "提交" });
		expect(button).toBeDisabled();
		expect(button).toHaveAttribute("aria-disabled", "true");

		const input = screen.getByLabelText("name");
		fireEvent.input(input, { target: { value: "Alice" } });

		expect(button).not.toBeDisabled();
		expect(button).toHaveAttribute("aria-disabled", "false");
	});

	it("enforces require-one and exclusive mode", () => {
		render(
			<>
				<FormValidationController />
				<form data-require-one="url,video_id" data-require-one-exclusive="true">
					<input aria-label="url" name="url" defaultValue="" />
					<input aria-label="video" name="video_id" defaultValue="" />
					<button type="submit">运行</button>
				</form>
			</>,
		);

		const submit = screen.getByRole("button", { name: "运行" });
		const url = screen.getByLabelText("url");
		const video = screen.getByLabelText("video");

		expect(submit).toBeDisabled();

		fireEvent.input(url, { target: { value: "https://example.com/video" } });
		expect(submit).not.toBeDisabled();

		fireEvent.input(video, { target: { value: "abc" } });
		expect(submit).toBeDisabled();
	});

	it("toggles dependent fields by checkbox controller", () => {
		render(
			<>
				<FormValidationController />
				<form>
					<label>
						<input type="checkbox" name="enabled" aria-label="enabled" />
						启用
					</label>
					<input
						name="email"
						aria-label="email"
						data-disabled-unless-checked="enabled"
						defaultValue="a@example.com"
					/>
					<button type="submit">保存</button>
				</form>
			</>,
		);

		const email = screen.getByLabelText("email") as HTMLInputElement;
		const enabled = screen.getByLabelText("enabled");

		expect(email.disabled).toBe(true);
		expect(email).toHaveAttribute("aria-disabled", "true");

		fireEvent.change(enabled, { target: { checked: true } });

		expect(email.disabled).toBe(false);
		expect(email).toHaveAttribute("aria-disabled", "false");
	});

	it("ignores forms without a submit control", () => {
		render(
			<>
				<FormValidationController />
				<form data-auto-disable-required="true">
					<input aria-label="standalone-required" name="name" required defaultValue="" />
				</form>
			</>,
		);

		const input = screen.getByLabelText("standalone-required");
		fireEvent.input(input, { target: { value: "ok" } });
		expect(input).toHaveValue("ok");
	});

	it("ignores non-element input events and empty dependent controller names", () => {
		render(
			<>
				<FormValidationController />
				<form>
					<input
						name="email"
						aria-label="email-with-empty-controller"
						data-disabled-unless-checked=""
						defaultValue="a@example.com"
					/>
					<button type="submit">保存</button>
				</form>
			</>,
		);

		const email = screen.getByLabelText("email-with-empty-controller");
		fireEvent(
			document,
			new Event("input", {
				bubbles: true,
				cancelable: true,
			}),
		);
		expect(email).toHaveValue("a@example.com");
	});
});
