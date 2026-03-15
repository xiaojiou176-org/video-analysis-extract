#!/usr/bin/env python3
"""Probe all configured RSSHub fallback nodes and optionally write the ranked list back to .env.

Usage:
  # Just print ranked list (dry-run):
  python scripts/runtime/probe_rsshub_health.py

  # Write best-N nodes back to RSSHUB_FALLBACK_BASE_URLS in .env:
  python scripts/runtime/probe_rsshub_health.py --write-env

  # Probe a custom list (overrides .env):
  python scripts/runtime/probe_rsshub_health.py --nodes "https://rsshub.app,https://hub.slarker.me"

Options:
  --write-env          Rewrite RSSHUB_FALLBACK_BASE_URLS in .env with ranked healthy nodes
  --env-file PATH      Path to .env file (default: .env in repo root)
  --nodes URL,...      Comma-separated override list (skips .env node list)
  --top N              Keep only top-N nodes in the written list (default: 8)
  --probe-path PATH    RSSHub route used for quality probe (default: /healthz)
  --timeout SECS       Per-probe timeout in seconds (default: 6)
  --concurrency N      Max concurrent probes (default: 10)
  --bilibili-uid UID   UID used in Bilibili probe path (default: 1132916)
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
import time
from pathlib import Path
from typing import NamedTuple

import httpx

# ---------------------------------------------------------------------------
# Default public RSSHub node list (from Grok research, 2026-02)
# ---------------------------------------------------------------------------
DEFAULT_NODES: list[str] = [
    "https://rsshub.top",
    "https://rss.hee.ink",
    "https://rsshub.rssforever.com",
    "https://hub.slarker.me",
    "https://rsshub.liumingye.cn",
    "https://rsshub.ktachibana.party",
    "https://rsshub.gujiakai.top",
    "https://rsshub.pseudoyu.com",
]


class ProbeResult(NamedTuple):
    base_url: str
    score: float
    latency_ms: float
    healthy: bool
    detail: str


async def _probe_node(
    client: httpx.AsyncClient,
    base_url: str,
    *,
    bilibili_uid: str,
    timeout: float,
) -> ProbeResult:
    score = 0.0
    latency_total_ms = 0.0
    details: list[str] = []

    # Step 1: /healthz
    health_url = f"{base_url}/healthz"
    t0 = time.monotonic()
    try:
        resp = await client.get(health_url, timeout=httpx.Timeout(timeout), follow_redirects=True)
        elapsed_ms = (time.monotonic() - t0) * 1000
        latency_total_ms += elapsed_ms
        if 200 <= resp.status_code < 300:
            score += 2.0
            details.append(f"healthz=OK({resp.status_code},{elapsed_ms:.0f}ms)")
        elif resp.status_code < 500:
            score += 0.5
            details.append(f"healthz={resp.status_code}({elapsed_ms:.0f}ms)")
        else:
            score -= 1.0
            details.append(f"healthz={resp.status_code}({elapsed_ms:.0f}ms)")
    except Exception as exc:
        latency_total_ms += (time.monotonic() - t0) * 1000
        score -= 1.5
        details.append(f"healthz=ERR({type(exc).__name__})")

    # Step 2: Bilibili route quality probe
    probe_url = f"{base_url}/bilibili/user/video/{bilibili_uid}"
    t0 = time.monotonic()
    try:
        resp = await client.get(probe_url, timeout=httpx.Timeout(timeout), follow_redirects=True)
        elapsed_ms = (time.monotonic() - t0) * 1000
        latency_total_ms += elapsed_ms
        body = resp.text or ""
        if resp.status_code == 200 and "<rss" in body:
            score += 3.0
            details.append(f"bili=RSS({elapsed_ms:.0f}ms)")
        elif "-352" in body or "风控" in body or "412 Precondition" in body:
            score -= 1.0
            details.append(f"bili=RISK({elapsed_ms:.0f}ms)")
        elif resp.status_code < 500:
            score += 0.25
            details.append(f"bili={resp.status_code}({elapsed_ms:.0f}ms)")
        else:
            score -= 1.0
            details.append(f"bili={resp.status_code}({elapsed_ms:.0f}ms)")
    except Exception as exc:
        latency_total_ms += (time.monotonic() - t0) * 1000
        score -= 1.0
        details.append(f"bili=ERR({type(exc).__name__})")

    healthy = score > 0
    return ProbeResult(
        base_url=base_url,
        score=round(score, 3),
        latency_ms=round(latency_total_ms, 1),
        healthy=healthy,
        detail=", ".join(details),
    )


async def probe_all(
    nodes: list[str],
    *,
    bilibili_uid: str,
    timeout: float,
    concurrency: int,
) -> list[ProbeResult]:
    sem = asyncio.Semaphore(concurrency)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    }

    async def probe_one(base_url: str) -> ProbeResult:
        async with sem, httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            return await _probe_node(client, base_url, bilibili_uid=bilibili_uid, timeout=timeout)

    tasks = [probe_one(node) for node in nodes]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    out: list[ProbeResult] = []
    for node, result in zip(nodes, results, strict=False):
        if isinstance(result, Exception):
            out.append(ProbeResult(node, -99.0, 0.0, False, f"GATHER_ERR({result})"))
        else:
            out.append(result)
    out.sort(key=lambda r: (r.healthy, r.score), reverse=True)
    return out


def _load_nodes_from_env(env_file: Path) -> list[str]:
    """Read RSSHUB_FALLBACK_BASE_URLS from the given .env file."""
    if not env_file.exists():
        return []
    content = env_file.read_text()
    match = re.search(r"RSSHUB_FALLBACK_BASE_URLS=['\"]?([^'\"#\n]+)['\"]?", content)
    if not match:
        return []
    raw = match.group(1).strip().strip("'\"")
    return [u.strip() for u in raw.split(",") if u.strip()]


def _write_env_var(env_file: Path, key: str, value: str) -> None:
    """Upsert a variable in an export-style .env file."""
    content = env_file.read_text() if env_file.exists() else ""
    export_pattern = re.compile(rf"^(export\s+)?{re.escape(key)}=.*$", re.MULTILINE)
    new_line = f"export {key}='{value}'"
    if export_pattern.search(content):
        content = export_pattern.sub(new_line, content, count=1)
    else:
        content = content.rstrip("\n") + f"\n{new_line}\n"
    env_file.write_text(content)


def _print_results(results: list[ProbeResult], top: int) -> None:
    width = max(len(r.base_url) for r in results) + 2
    print(f"\n{'RANK':<5} {'NODE':<{width}} {'SCORE':>6} {'LATENCY':>10} {'STATUS':<8} DETAIL")
    print("-" * (width + 45))
    for i, r in enumerate(results, 1):
        status = "HEALTHY" if r.healthy else "UNHEALTHY"
        marker = " ← top-{top}" if i == top else ""
        if i == top:
            marker = f"  ← top-{top} cutoff"
        print(
            f"{i:<5} {r.base_url:<{width}} {r.score:>6.2f} {r.latency_ms:>8.0f}ms "
            f"{status:<9}{marker}"
        )
        print(f"      {r.detail}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--write-env", action="store_true", help="Write ranked list back to .env")
    parser.add_argument("--env-file", default=None, help="Path to .env file")
    parser.add_argument("--nodes", default=None, help="Comma-separated node URL list")
    parser.add_argument(
        "--top", type=int, default=8, help="Keep top-N nodes when writing (default: 8)"
    )
    parser.add_argument(
        "--timeout", type=float, default=6.0, help="Per-probe timeout seconds (default: 6)"
    )
    parser.add_argument(
        "--concurrency", type=int, default=10, help="Max concurrent probes (default: 10)"
    )
    parser.add_argument("--bilibili-uid", default="1132916", help="Bilibili UID for quality probe")
    args = parser.parse_args()

    # Resolve .env path
    repo_root = Path(__file__).resolve().parents[2]
    env_file = Path(args.env_file) if args.env_file else repo_root / ".env"

    # Resolve node list
    if args.nodes:
        nodes = [n.strip() for n in args.nodes.split(",") if n.strip()]
    else:
        nodes = _load_nodes_from_env(env_file)
        if not nodes:
            print(
                f"[info] RSSHUB_FALLBACK_BASE_URLS not set in {env_file}; using built-in default list."
            )
            nodes = DEFAULT_NODES

    print(
        f"[probe] Probing {len(nodes)} RSSHub nodes (timeout={args.timeout}s, concurrency={args.concurrency})…"
    )
    t_start = time.monotonic()
    results = asyncio.run(
        probe_all(
            nodes,
            bilibili_uid=args.bilibili_uid,
            timeout=args.timeout,
            concurrency=args.concurrency,
        )
    )
    elapsed = time.monotonic() - t_start
    print(f"[probe] Done in {elapsed:.1f}s.")

    _print_results(results, args.top)

    healthy_nodes = [r.base_url for r in results if r.healthy]
    top_nodes = healthy_nodes[: args.top] if args.top > 0 else healthy_nodes

    print(f"[summary] {len(healthy_nodes)}/{len(results)} nodes healthy.")
    if top_nodes:
        print(f"[summary] Top-{len(top_nodes)} nodes:")
        for i, node in enumerate(top_nodes, 1):
            print(f"  {i}. {node}")

    if args.write_env:
        if not top_nodes:
            print("[warn] No healthy nodes found; .env will NOT be updated.", file=sys.stderr)
            sys.exit(1)
        value = ",".join(top_nodes)
        _write_env_var(env_file, "RSSHUB_FALLBACK_BASE_URLS", value)
        print(f"\n[write] Updated RSSHUB_FALLBACK_BASE_URLS in {env_file}")
        print(f"        Value: {value}")
    else:
        print("\n[hint] Run with --write-env to persist this ranking to .env.")


if __name__ == "__main__":
    main()
