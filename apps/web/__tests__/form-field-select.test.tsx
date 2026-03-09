import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FormCheckboxField, FormInputField, FormSelectField } from "@/components/form-field";

describe("FormSelectField", () => {
	it("falls back to generated field id when name is omitted", () => {
		render(
			<FormSelectField
				label="分类"
				options={[
					{ value: "", label: "全部分类" },
					{ value: "tech", label: "科技" },
				]}
			/>,
		);

		const trigger = screen.getByRole("combobox", { name: "分类" });
		expect(trigger.id).toMatch(/^field-/);
		expect(trigger).toHaveAttribute("data-slot", "select-trigger");
		expect(screen.getByDisplayValue("")).toBeInTheDocument();
	});

	it("maps empty option through the shadcn select and hidden input", () => {
		render(
			<FormSelectField
				label="来源"
				name="source"
				defaultValue="tech"
				options={[
					{ value: "", label: "全部来源" },
					{ value: "tech", label: "科技" },
				]}
			/>,
		);

		expect(screen.getByDisplayValue("tech")).toBeInTheDocument();
		fireEvent.click(screen.getByRole("combobox", { name: "来源" }));
		fireEvent.click(screen.getByRole("option", { name: "全部来源" }));
		expect(screen.getByDisplayValue("")).toBeInTheDocument();
	});

	it("supports controlled select values and non-string labels", () => {
		render(
			<FormSelectField
				label={<span>模式</span>}
				name="mode"
				value="creator"
				options={[
					{ value: "", label: "全部模式" },
					{ value: "creator", label: <strong>创作者</strong> },
				]}
			/>,
		);

		expect(screen.getByDisplayValue("creator")).toBeInTheDocument();
		expect(screen.getByRole("combobox")).toHaveAttribute("data-slot", "select-trigger");
	});
});

describe("FormCheckboxField", () => {
	it("uses the shared checkbox primitive and mirrors state into a hidden input", () => {
		render(<FormCheckboxField label="启用订阅" name="enabled" defaultChecked={false} />);

		const checkbox = screen.getByRole("checkbox", { name: "启用订阅" });
		expect(checkbox).toHaveAttribute("data-slot", "checkbox");
		expect(screen.getByDisplayValue("")).toHaveAttribute("name", "enabled");

		fireEvent.click(checkbox);
		expect(screen.getByDisplayValue("on")).toBeInTheDocument();
	});

	it("supports controlled checkbox state and forwards onChange payload", () => {
		const handleChange = vi.fn();
		render(
			<FormCheckboxField
				label="启用通知"
				name="notify"
				checked
				onChange={handleChange}
			/>,
		);

		const checkbox = screen.getByRole("checkbox", { name: "启用通知" });
		expect(checkbox).toBeChecked();
		fireEvent.click(checkbox);
		expect(handleChange).toHaveBeenCalledTimes(1);
	});
});

describe("FormInputField", () => {
	it("renders hint and error ids into aria-describedby", () => {
		render(
			<FormInputField
				label="标题"
				name="title"
				hint="请输入标题"
				error="标题不能为空"
			/>,
		);

		const input = screen.getByRole("textbox", { name: "标题" });
		const describedBy = input.getAttribute("aria-describedby") ?? "";
		expect(describedBy).toContain("hint");
		expect(describedBy).toContain("error");
		expect(screen.getByText("请输入标题")).toBeInTheDocument();
		expect(screen.getByRole("alert")).toHaveTextContent("标题不能为空");
	});

	it("supports custom id and aria-invalid without hint/error content", () => {
		render(
			<FormInputField
				label="摘要链接"
				name="artifactUrl"
				id="custom-artifact-url"
				aria-invalid
			/>,
		);

		const input = screen.getByRole("textbox", { name: "摘要链接" });
		expect(input).toHaveAttribute("id", "custom-artifact-url");
		expect(input).toHaveAttribute("aria-invalid", "true");
		expect(input).not.toHaveAttribute("aria-describedby");
	});
});

describe("FormSelectField advanced branches", () => {
	it("uses generic placeholder and empty hidden value when no options are provided", () => {
		const { container } = render(
			<FormSelectField label={<span>筛选模式</span>} name="mode" options={[]} />,
		);

		const trigger = screen.getByRole("combobox");
		expect(trigger).not.toHaveAttribute("aria-label");
		expect(trigger.querySelector('[data-slot="select-value"]')).toBeEmptyDOMElement();
		expect(container.querySelector('input[type=\"hidden\"][name=\"mode\"]')).toHaveValue("");
	});

	it("merges external aria-describedby with hint and error ids", () => {
		render(
			<FormSelectField
				label="状态"
				name="status"
				aria-describedby="external-desc"
				hint="可选择任务状态"
				error="请选择有效状态"
				options={[
					{ value: "", label: "全部状态" },
					{ value: "queued", label: "排队中", disabled: true },
				]}
			/>,
		);

		const trigger = screen.getByRole("combobox", { name: "状态" });
		const describedBy = trigger.getAttribute("aria-describedby") ?? "";
		expect(describedBy).toContain("external-desc");
		expect(describedBy).toContain("hint");
		expect(describedBy).toContain("error");
		fireEvent.click(trigger);
		expect(screen.getByRole("option", { name: "排队中" })).toHaveAttribute("aria-disabled", "true");
	});
});

describe("FormCheckboxField advanced branches", () => {
	it("combines described-by sources and mirrors unchecked value", () => {
		const { container } = render(
			<FormCheckboxField
				label="启用每日推送"
				name="dailyDigest"
				defaultChecked
				aria-describedby="external-checkbox"
				hint="每天推送一次"
			/>,
		);

		const checkbox = screen.getByRole("checkbox", { name: "启用每日推送" });
		const describedBy = checkbox.getAttribute("aria-describedby") ?? "";
		expect(describedBy).toContain("external-checkbox");
		expect(describedBy).toContain("hint");

		fireEvent.click(checkbox);
		expect(container.querySelector('input[type=\"hidden\"][name=\"dailyDigest\"]')).toHaveValue("");
		expect(screen.getByText("每天推送一次")).toBeInTheDocument();
	});

	it("updates uncontrolled select to a non-empty option and uses string aria-label", () => {
		render(
			<FormSelectField
				label="分类"
				name="category"
				defaultValue=""
				options={[
					{ value: "", label: "全部分类" },
					{ value: "ops", label: "运维" },
				]}
			/>,
		);

		const trigger = screen.getByRole("combobox", { name: "分类" });
		fireEvent.click(trigger);
		fireEvent.click(screen.getByRole("option", { name: "运维" }));
		expect(screen.getByDisplayValue("ops")).toBeInTheDocument();
		expect(trigger).toHaveAttribute("aria-label", "分类");
	});

	it("mirrors false checkbox state into hidden input and renders checkbox error", () => {
		render(
			<FormCheckboxField
				label="启用高级模式"
				name="advanced"
				error="必须确认"
				defaultChecked={false}
			/>,
		);

		expect(screen.getByDisplayValue("")).toHaveAttribute("name", "advanced");
		expect(screen.getByRole("alert")).toHaveTextContent("必须确认");
	});

	it("keeps hidden input unchanged for controlled checkbox while emitting unchecked change", () => {
		const handleChange = vi.fn();
		render(
			<FormCheckboxField
				label="受控模式"
				name="controlled"
				checked
				onChange={handleChange}
			/>,
		);

		const checkbox = screen.getByRole("checkbox", { name: "受控模式" });
		fireEvent.click(checkbox);
		expect(screen.getByDisplayValue("on")).toHaveAttribute("name", "controlled");
		expect(handleChange).toHaveBeenCalledTimes(1);
		expect(handleChange.mock.calls[0]?.[0]?.target?.checked).toBe(false);
		expect(handleChange.mock.calls[0]?.[0]?.target?.value).toBe("");
	});
});
