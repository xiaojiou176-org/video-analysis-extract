#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="http://127.0.0.1:8000"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-base-url)
      API_BASE_URL="$2"
      shift 2
      ;;
    *)
      echo "[smoke_computer_use_local] unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

payload="$(
  python3 - <<'PY'
import base64
import json
import struct
import zlib

def generate_png_base64(width: int = 64, height: int = 64) -> str:
    signature = b"\x89PNG\r\n\x1a\n"
    row = b"\x00" + (b"\x66\xaa\xff" * width)  # filter byte + RGB pixels
    raw = row * height
    compressed = zlib.compress(raw, level=9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    idat = chunk(b"IDAT", compressed)
    iend = chunk(b"IEND", b"")
    png = signature + ihdr + idat + iend
    return base64.b64encode(png).decode("ascii")

print(json.dumps({
    "instruction": "Open settings and click submit button",
    "screenshot_base64": generate_png_base64(),
    "safety": {
        "confirm_before_execute": True,
        "blocked_actions": ["submit"],
        "max_actions": 5
    }
}))
PY
)"

tmp_body="$(mktemp)"
status="$(
  curl -sS -o "$tmp_body" -w '%{http_code}' \
    -H 'Accept: application/json' \
    -H 'Content-Type: application/json' \
    -X POST "${API_BASE_URL}/api/v1/computer-use/run" \
    --data "$payload"
)"
body="$(cat "$tmp_body")"
rm -f "$tmp_body"

if [[ "$status" != "200" ]]; then
  echo "[smoke_computer_use_local] status=${status} body=${body}" >&2
  exit 1
fi

BODY="$body" python3 - <<'PY'
import json, os, sys
obj = json.loads(os.environ["BODY"])
required = ["actions", "require_confirmation", "blocked_actions", "final_text", "thought_metadata"]
missing = [k for k in required if k not in obj]
if missing:
    print(f"missing fields: {missing}", file=sys.stderr)
    sys.exit(1)
if not isinstance(obj["actions"], list) or not obj["actions"]:
    print("actions empty", file=sys.stderr)
    sys.exit(1)
if "provider" not in (obj.get("thought_metadata") or {}):
    print("thought_metadata.provider missing", file=sys.stderr)
    sys.exit(1)
print("[smoke_computer_use_local] passed")
PY
