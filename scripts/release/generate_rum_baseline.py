#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _load_samples(path: Path) -> tuple[dict[str, Any], list[dict[str, float]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("input must be a JSON object")
    raw_samples = payload.get("samples")
    if not isinstance(raw_samples, list):
        raise ValueError("input.samples must be a list")

    normalized: list[dict[str, float]] = []
    for idx, item in enumerate(raw_samples):
        if not isinstance(item, dict):
            raise ValueError(f"samples[{idx}] must be an object")
        try:
            lcp = float(item["lcp_ms"])
            inp = float(item["inp_ms"])
            cls = float(item["cls"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"samples[{idx}] has invalid metric fields") from exc
        if lcp <= 0 or inp <= 0 or cls < 0 or cls > 1:
            raise ValueError(f"samples[{idx}] has out-of-range metric values")
        normalized.append({"lcp_ms": lcp, "inp_ms": inp, "cls": cls})
    if not normalized:
        raise ValueError("samples must not be empty")
    return payload, normalized


def _p75(values: list[float]) -> float:
    ordered = sorted(values)
    rank = max(0, (len(ordered) * 75 + 99) // 100 - 1)
    return ordered[rank]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate release-ready RUM baseline from raw samples")
    parser.add_argument("--input", default="reports/performance/rum-observations.json")
    parser.add_argument("--output", default="reports/performance/rum-baseline.json")
    parser.add_argument("--source", default="rum_observations")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    payload, samples = _load_samples(input_path)

    lcp_values = [item["lcp_ms"] for item in samples]
    inp_values = [item["inp_ms"] for item in samples]
    cls_values = [item["cls"] for item in samples]
    sample_size = len(samples)

    result = {
        "name": "video-analysis-rum-baseline",
        "version": "1.1.0",
        "source": args.source,
        "generated_at": datetime.now(UTC).isoformat(),
        "window_days": int(payload.get("window_days", 28)),
        "sample_source": payload.get("sample_source", "unknown"),
        "metrics": {
            "lcp_ms_p75": round(_p75(lcp_values), 2),
            "inp_ms_p75": round(_p75(inp_values), 2),
            "cls_p75": round(_p75(cls_values), 4),
            "sample_size": sample_size,
        },
        "notes": "Generated from raw RUM observations; do not hand-edit metrics.",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
