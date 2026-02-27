"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";

function isBlank(value: string | null | undefined): boolean {
	return !value || value.trim().length === 0;
}

function evaluateForm(form: HTMLFormElement): void {
	const submit = form.querySelector<HTMLButtonElement>(
		'button[type="submit"], input[type="submit"]',
	);
	if (!submit) {
		return;
	}

	let disabled = false;
	if (form.dataset.autoDisableRequired === "true") {
		const requiredFields = Array.from(
			form.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(
				"[required]",
			),
		);
		disabled = requiredFields.some(
			(field) => isBlank((field as HTMLInputElement).value) || !field.checkValidity(),
		);
	}

	const requireOne = form.dataset.requireOne;
	const requireOneExclusive = form.dataset.requireOneExclusive === "true";
	if (requireOne) {
		const names = requireOne
			.split(",")
			.map((item) => item.trim())
			.filter((item) => item.length > 0);
		if (names.length > 0) {
			const filledCount = names.filter((name) => {
				const field = form.querySelector<
					HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
				>(`[name="${name}"]`);
				return !isBlank(field?.value);
			}).length;
			disabled = disabled || filledCount < 1;
			if (requireOneExclusive && filledCount > 1) {
				disabled = true;
			}
		}
	}

	submit.disabled = disabled;
	submit.setAttribute("aria-disabled", disabled ? "true" : "false");

	const dependentFields = Array.from(
		form.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(
			"[data-disabled-unless-checked]",
		),
	);
	dependentFields.forEach((field) => {
		const controllerName = field.getAttribute("data-disabled-unless-checked");
		if (!controllerName) {
			return;
		}
		const controller = form.querySelector<HTMLInputElement>(
			`input[type="checkbox"][name="${controllerName}"]`,
		);
		const enabled = Boolean(controller?.checked);
		field.disabled = !enabled;
		field.setAttribute("aria-disabled", enabled ? "false" : "true");
	});
}

function evaluateAllForms(): void {
	const forms = new Set<HTMLFormElement>();
	document
		.querySelectorAll<Element>(
			"form[data-auto-disable-required], form[data-require-one], form [data-disabled-unless-checked]",
		)
		.forEach((node) => {
			if (node instanceof HTMLFormElement) {
				forms.add(node);
				return;
			}
			const parentForm = node.closest("form");
			if (parentForm instanceof HTMLFormElement) {
				forms.add(parentForm);
			}
		});
	forms.forEach((form) => {
		evaluateForm(form);
	});
}

export function FormValidationController(): null {
	const pathname = usePathname();

	useEffect(() => {
		void pathname;
		const onInput = (event: Event) => {
			const target = event.target;
			if (!(target instanceof Element)) {
				return;
			}
			const form = target.closest("form");
			if (form instanceof HTMLFormElement) {
				evaluateForm(form);
			}
		};

		evaluateAllForms();
		document.addEventListener("input", onInput, true);
		document.addEventListener("change", onInput, true);

		return () => {
			document.removeEventListener("input", onInput, true);
			document.removeEventListener("change", onInput, true);
		};
	}, [pathname]);

	return null;
}
