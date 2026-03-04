"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { getFlashMessage, toErrorCode } from "@/app/flash-message";
import { apiClient } from "@/lib/api/client";
import type { Subscription, SubscriptionCategory } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

const CATEGORIES: SubscriptionCategory[] = ["tech", "creator", "macro", "ops", "misc"];
const UNDO_WINDOW_MS = 10_000;
const CATEGORY_LABELS: Record<SubscriptionCategory, string> = {
	tech: "科技",
	creator: "创作者",
	macro: "宏观",
	ops: "运维",
	misc: "其他",
};

type Props = {
	subscriptions: Subscription[];
};

type UndoContext = {
	ids: string[];
	previousCategories: Record<string, SubscriptionCategory>;
	nextCategory: SubscriptionCategory;
	expiresAt: number;
};

type UndoHistory = {
	message: string;
	isError: boolean;
};

function getStatusChipFeedbackClass(status: string): string {
	const normalized = status.trim().toLowerCase();
	if (normalized === "running" || normalized === "queued" || normalized === "pending") {
		return "status-chip-feedback status-chip-is-updating";
	}
	if (normalized === "succeeded" || normalized === "enabled") {
		return "status-chip-feedback status-chip-is-confirmed";
	}
	return "status-chip-feedback";
}

export function SubscriptionBatchPanel({ subscriptions }: Props) {
	const router = useRouter();
	const [visibleSubscriptions, setVisibleSubscriptions] = useState<Subscription[]>(subscriptions);
	const [selected, setSelected] = useState<Set<string>>(new Set());
	const [batchCategory, setBatchCategory] = useState<SubscriptionCategory>("misc");
	const [applying, setApplying] = useState(false);
	const [undoing, setUndoing] = useState(false);
	const [applyResult, setApplyResult] = useState<string | null>(null);
	const [undoContext, setUndoContext] = useState<UndoContext | null>(null);
	const [undoRemainingSeconds, setUndoRemainingSeconds] = useState(0);
	const [undoHistory, setUndoHistory] = useState<UndoHistory | null>(null);
	// 二步确认：存储待删除的 ID
	const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
	const [deletingId, setDeletingId] = useState<string | null>(null);
	const [deleteStatusMessage, setDeleteStatusMessage] = useState("");
	const confirmDeleteRefs = useRef<Record<string, HTMLButtonElement | null>>({});
	const deleteTriggerRefs = useRef<Record<string, HTMLButtonElement | null>>({});
	const selectAllRef = useRef<HTMLInputElement | null>(null);
	const restoreDeleteTriggerFocusIdRef = useRef<string | null>(null);
	const undoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const undoCountdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

	function clearUndoTimer() {
		if (!undoTimerRef.current) {
			if (undoCountdownRef.current) {
				clearInterval(undoCountdownRef.current);
				undoCountdownRef.current = null;
			}
			return;
		}
		clearTimeout(undoTimerRef.current);
		undoTimerRef.current = null;
		if (undoCountdownRef.current) {
			clearInterval(undoCountdownRef.current);
			undoCountdownRef.current = null;
		}
	}

	function clearUndoContext() {
		clearUndoTimer();
		setUndoContext(null);
		setUndoRemainingSeconds(0);
	}

	useEffect(() => {
		setVisibleSubscriptions(subscriptions);
	}, [subscriptions]);

	useEffect(() => {
		if (!pendingDeleteId) {
			return;
		}
		confirmDeleteRefs.current[pendingDeleteId]?.focus();
	}, [pendingDeleteId]);

	useEffect(() => {
		if (pendingDeleteId || deletingId || !restoreDeleteTriggerFocusIdRef.current) {
			return;
		}
		const targetId = restoreDeleteTriggerFocusIdRef.current;
		restoreDeleteTriggerFocusIdRef.current = null;
		deleteTriggerRefs.current[targetId]?.focus();
	}, [pendingDeleteId, deletingId]);

	useEffect(() => {
		if (!selectAllRef.current) {
			return;
		}
		const hasSelection = selected.size > 0;
		const partialSelection = hasSelection && selected.size < visibleSubscriptions.length;
		selectAllRef.current.indeterminate = partialSelection;
	}, [selected, visibleSubscriptions.length]);

	useEffect(() => {
		return () => {
			clearUndoTimer();
		};
	}, []);

	useEffect(() => {
		if (!undoContext) {
			return;
		}
		const updateRemaining = () => {
			const remainingMs = undoContext.expiresAt - Date.now();
			setUndoRemainingSeconds(Math.max(0, Math.ceil(remainingMs / 1000)));
		};
		updateRemaining();
		undoCountdownRef.current = setInterval(updateRemaining, 1000);
		undoTimerRef.current = setTimeout(() => {
			setUndoContext(null);
			setUndoRemainingSeconds(0);
			setUndoHistory({
				message: "批量分类撤销窗口已结束。",
				isError: false,
			});
			if (undoCountdownRef.current) {
				clearInterval(undoCountdownRef.current);
				undoCountdownRef.current = null;
			}
			undoTimerRef.current = null;
		}, Math.max(0, undoContext.expiresAt - Date.now()));
		return () => {
			clearUndoTimer();
		};
	}, [undoContext]);

	function toggleAll() {
		if (selected.size === visibleSubscriptions.length) {
			setSelected(new Set());
		} else {
			setSelected(new Set(visibleSubscriptions.map((s) => s.id)));
		}
	}

	function toggleOne(id: string) {
		setSelected((prev) => {
			const next = new Set(prev);
			if (next.has(id)) {
				next.delete(id);
			} else {
				next.add(id);
			}
			return next;
		});
	}

	function getCategoryLabel(category: SubscriptionCategory): string {
		return CATEGORY_LABELS[category];
	}

	async function handleDeleteConfirm(id: string) {
		const targetName = getSubscriptionDisplayNameById(id);
		setDeletingId(id);
		setPendingDeleteId(null);
		setDeleteStatusMessage(`正在删除「${targetName}」。`);
		try {
			await apiClient.deleteSubscription(id);
			setVisibleSubscriptions((prev) => prev.filter((item) => item.id !== id));
			setSelected((prev) => {
				const next = new Set(prev);
				next.delete(id);
				return next;
			});
			setApplyResult("订阅已删除。");
			setDeleteStatusMessage(`已删除「${targetName}」。`);
			router.replace("/subscriptions?status=success&code=SUBSCRIPTION_DELETED");
			router.refresh();
		} catch (err) {
			const message = `删除失败：${getFlashMessage(toErrorCode(err))}`;
			setApplyResult(message);
			setDeleteStatusMessage(`删除「${targetName}」失败，请稍后重试。`);
			restoreDeleteTriggerFocusIdRef.current = id;
		} finally {
			setDeletingId(null);
		}
	}

	async function handleApplyCategory() {
		if (selected.size === 0) {
			return;
		}
		const selectedIds = Array.from(selected);
		const previousCategories: Record<string, SubscriptionCategory> = {};
		visibleSubscriptions.forEach((item) => {
			if (selected.has(item.id)) {
				previousCategories[item.id] = item.category;
			}
		});
		clearUndoContext();
		setApplying(true);
		setApplyResult(null);
		try {
			const result = await apiClient.batchUpdateSubscriptionCategory({
				ids: selectedIds,
				category: batchCategory,
			});
			setVisibleSubscriptions((prev) =>
				prev.map((item) =>
					selectedIds.includes(item.id) ? { ...item, category: batchCategory } : item,
				),
			);
			setUndoContext({
				ids: selectedIds,
				previousCategories,
				nextCategory: batchCategory,
				expiresAt: Date.now() + UNDO_WINDOW_MS,
			});
			setUndoHistory(null);
			setApplyResult(`已将 ${result.updated} 条订阅移至分类「${getCategoryLabel(batchCategory)}」`);
			setSelected(new Set());
			router.refresh();
		} catch (err) {
			setApplyResult(`操作失败：${getFlashMessage(toErrorCode(err))}`);
		} finally {
			setApplying(false);
		}
	}

	async function handleUndoCategory() {
		if (!undoContext) {
			return;
		}
		setUndoing(true);
		setApplyResult(null);
		try {
			const idsByCategory = new Map<SubscriptionCategory, string[]>();
			undoContext.ids.forEach((id) => {
				const oldCategory = undoContext.previousCategories[id];
				const bucket = idsByCategory.get(oldCategory) ?? [];
				bucket.push(id);
				idsByCategory.set(oldCategory, bucket);
			});

			await Promise.all(
				Array.from(idsByCategory.entries()).map(([category, ids]) =>
					apiClient.batchUpdateSubscriptionCategory({ ids, category }),
				),
			);

			setVisibleSubscriptions((prev) =>
				prev.map((item) => {
					const previousCategory = undoContext.previousCategories[item.id];
					return previousCategory ? { ...item, category: previousCategory } : item;
				}),
			);
			clearUndoContext();
			setUndoHistory({
				message: `已恢复 ${undoContext.ids.length} 条订阅至原分类。`,
				isError: false,
			});
			setApplyResult(
				`已撤销分类变更，恢复 ${undoContext.ids.length} 条订阅至原分类。`,
			);
			router.refresh();
		} catch (err) {
			setUndoHistory({
				message: "上次撤销失败，请稍后重试。",
				isError: true,
			});
			setApplyResult(`撤销失败：${getFlashMessage(toErrorCode(err))}`);
		} finally {
			setUndoing(false);
		}
	}

	const allSelected =
		visibleSubscriptions.length > 0 && selected.size === visibleSubscriptions.length;
	const selectedSummary = `${selected.size}/${visibleSubscriptions.length}`;
	const isApplyError = Boolean(
		applyResult &&
			(applyResult.startsWith("操作失败") ||
				applyResult.startsWith("删除失败") ||
				applyResult.startsWith("撤销失败")),
	);

	function getSubscriptionDisplayName(item: Subscription) {
		const sourceName = item.source_name?.trim();
		const sourceValue = item.source_value?.trim();
		return sourceName || sourceValue || `订阅 ${item.id}`;
	}

	function getSubscriptionDisplayNameById(id: string): string {
		const target = visibleSubscriptions.find((item) => item.id === id);
		return target ? getSubscriptionDisplayName(target) : `订阅 ${id}`;
	}

	return (
		<div className="stack">
			{visibleSubscriptions.length === 0 ? (
				<p className="small">暂无订阅数据。</p>
			) : (
				<>
					<div className="table-scroll">
						<table>
							<caption className="sr-only">当前订阅列表</caption>
							<thead>
								<tr>
									<th scope="col">
										<input
											ref={selectAllRef}
											type="checkbox"
											checked={allSelected}
											onChange={toggleAll}
											aria-label={`全选（已选 ${selectedSummary}）`}
										/>
									</th>
									<th scope="col">来源</th>
									<th scope="col">平台 / 类型</th>
									<th scope="col">分类 / 优先级</th>
									<th scope="col">启用</th>
									<th scope="col">更新时间</th>
									<th scope="col">操作</th>
								</tr>
							</thead>
							<tbody>
								{visibleSubscriptions.map((item) => {
									const isSelected = selected.has(item.id);
									const rowState =
										deletingId === item.id
											? "deleting"
											: pendingDeleteId === item.id
												? "confirming-delete"
												: undefined;
									return (
									<tr
										key={item.id}
										className={isSelected ? "row-selected" : undefined}
										data-state={rowState}
									>
										<td>
											<input
												type="checkbox"
												checked={isSelected}
												onChange={() => toggleOne(item.id)}
												aria-label={`选择 ${getSubscriptionDisplayName(item)}`}
											/>
										</td>
										<td>
											<div className="sub-source-name">{getSubscriptionDisplayName(item)}</div>
											<div className="small">
												{item.adapter_type}
												{item.source_url
													? ` · ${item.source_url}`
													: item.rsshub_route
														? ` · ${item.rsshub_route}`
														: ""}
											</div>
										</td>
										<td>
											<div>{item.platform}</div>
											<div className="small">{item.source_type}</div>
										</td>
										<td>
											<div className="sub-category-badge" data-category={item.category}>
												{getCategoryLabel(item.category)}
											</div>
											<div className="small">
												优先级 {item.priority}
												{item.tags.length > 0 ? ` · ${item.tags.join(", ")}` : ""}
											</div>
										</td>
										<td>
											<span
												className={`status-chip ${getStatusChipFeedbackClass(
													item.enabled ? "enabled" : "failed",
												)} ${item.enabled ? "status-succeeded" : "status-failed"}`}
											>
												{item.enabled ? "启用" : "停用"}
											</span>
										</td>
										<td className="small">{formatDateTime(item.updated_at)}</td>
										<td>
									{pendingDeleteId === item.id ? (
												<span className="inline">
													<button
														ref={(element) => {
															confirmDeleteRefs.current[item.id] = element;
														}}
														type="button"
														className="destructive"
														disabled={deletingId === item.id}
														onClick={() => handleDeleteConfirm(item.id)}
														data-interaction="cta"
													>
														{deletingId === item.id
															? "删除中…"
															: `确认删除「${getSubscriptionDisplayName(item)}」`}
													</button>
														<button
															type="button"
															onClick={() => {
																restoreDeleteTriggerFocusIdRef.current = item.id;
																setPendingDeleteId(null);
																setDeleteStatusMessage("已取消删除。");
															}}
															data-interaction="control"
														>
														取消
													</button>
												</span>
											) : (
												<button
													ref={(element) => {
														deleteTriggerRefs.current[item.id] = element;
													}}
													type="button"
													className="btn-ghost-danger"
													disabled={deletingId === item.id}
													onClick={() => {
														setPendingDeleteId(item.id);
														setDeleteStatusMessage(
															`已进入删除确认，目标为 ${getSubscriptionDisplayName(item)}。`,
														);
													}}
													data-interaction="cta"
												>
													删除
												</button>
											)}
										</td>
									</tr>
									);
								})}
							</tbody>
						</table>
					</div>

					{selected.size > 0 && (
						<div className="batch-action-bar">
							<span className="small">
								已选 <strong>{selected.size}</strong> 条
							</span>
							<div className="inline">
								<label className="batch-category-label">
									批量设分类
									<select
										value={batchCategory}
										onChange={(e) => setBatchCategory(e.target.value as SubscriptionCategory)}
									>
										{CATEGORIES.map((c) => (
											<option key={c} value={c}>
												{getCategoryLabel(c)}
											</option>
										))}
									</select>
								</label>
								<button
									type="button"
									className={applying ? "primary btn-feedback-pending" : "primary"}
									disabled={applying || undoing}
									onClick={handleApplyCategory}
									data-interaction="cta"
									data-feedback-state={applying ? "pending" : "idle"}
									aria-busy={applying}
								>
									{applying ? "应用分类中…" : "应用分类"}
								</button>
								<button type="button" onClick={() => setSelected(new Set())} data-interaction="control">
									取消选择
								</button>
							</div>
						</div>
					)}

					{applyResult && (
						<p
							className={isApplyError ? "alert error" : "alert success"}
							role={isApplyError ? "alert" : "status"}
							aria-live={isApplyError ? "assertive" : "polite"}
						>
							{applyResult}
						</p>
					)}
					{undoContext && (
						<p className="alert" role="status" aria-live="polite">
							已将 {undoContext.ids.length} 条订阅从「
							{getCategoryLabel(undoContext.nextCategory)}
							」更新，可在 {undoRemainingSeconds} 秒内撤销。
							<button
								type="button"
								onClick={handleUndoCategory}
								disabled={undoing || applying}
								data-interaction="control"
							>
								{undoing ? "撤销中…" : "撤销"}
							</button>
						</p>
					)}
					{undoHistory && (
						<p
							className={undoHistory.isError ? "alert error" : "alert"}
							role={undoHistory.isError ? "alert" : "status"}
							aria-live={undoHistory.isError ? "assertive" : "polite"}
							aria-atomic="true"
						>
							{undoHistory.message}
						</p>
					)}
					<output className="sr-only" aria-live="polite" aria-atomic="true">
						{deleteStatusMessage}
					</output>
				</>
			)}
		</div>
	);
}
