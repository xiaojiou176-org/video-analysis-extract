"use client";

import type { ComponentProps } from "react";
import { useId } from "react";
import { useFormStatus } from "react-dom";

type SubmitButtonProps = Omit<ComponentProps<"button">, "type" | "disabled"> & {
	pendingLabel?: string;
	statusText?: string;
};

export function SubmitButton({
	children,
	className = "primary",
	pendingLabel = "提交中…",
	statusText,
	"aria-describedby": ariaDescribedBy,
	...props
}: SubmitButtonProps) {
	const { pending } = useFormStatus();
	const statusId = useId();
	const state = pending ? "pending" : "idle";
	const describedBy = [ariaDescribedBy, statusId].filter(Boolean).join(" ");
	const buttonLabel = pending ? (
		<span className="inline" data-part="button-content" data-state={state}>
			<span
				className="status-chip status-running"
				data-part="pending-indicator"
				data-state={state}
				aria-hidden="true"
			>
				•
			</span>
			<span data-part="button-label" data-state={state}>
				{pendingLabel}
			</span>
			<span className="sr-only">正在提交，请稍候。</span>
		</span>
	) : (
		<span className="inline" data-part="button-content" data-state={state}>
			<span data-part="button-label" data-state={state}>
				{children}
			</span>
		</span>
	);
	const pendingStatusText = statusText ?? pendingLabel;
	const buttonClassName = pending ? `${className} btn-feedback-pending` : className;

	return (
		<>
			<button
				{...props}
				type="submit"
				className={buttonClassName}
				disabled={pending}
				aria-disabled={pending ? "true" : "false"}
				aria-busy={pending ? "true" : "false"}
				aria-describedby={describedBy}
				data-state={state}
				data-feedback-state={state}
				data-interaction="cta"
			>
				{buttonLabel}
			</button>
			<output id={statusId} className="sr-only" role="status" aria-live="polite" aria-atomic="true">
				{pending ? pendingStatusText : ""}
			</output>
		</>
	);
}
