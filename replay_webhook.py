#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx"]
# ///
"""
Replay webhook payloads captured in daemon debug logs.

Usage:
    python replay_webhook.py debug/20260309-003025.log          # replay all payloads
    python replay_webhook.py debug/20260309-003025.log --index 0  # replay first payload only
    python replay_webhook.py debug/20260309-003025.log --list     # list found payloads

The daemon must be running and reachable at DAEMON_URL (default: http://localhost:3000).
"""

import argparse
import json
import re
import sys

import httpx

DAEMON_URL = "http://localhost:3000"
MARKER = "Raw webhook payload:"


def extract_payloads(log_path: str) -> list[tuple[str, dict]]:
    """Return list of (timestamp, payload_dict) from a debug log file."""
    payloads = []
    with open(log_path) as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+).*" + re.escape(MARKER), line)
        if match:
            timestamp = match.group(1)
            # Collect JSON lines until we hit the next log line (timestamp prefix) or EOF
            json_lines = []
            i += 1
            while i < len(lines):
                next_line = lines[i]
                # Log lines start with a timestamp pattern — end of this payload
                if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+", next_line):
                    break
                # Skip uvicorn access log lines interleaved in the JSON output
                if re.match(r"INFO:\s+", next_line):
                    i += 1
                    continue
                json_lines.append(next_line)
                i += 1
            raw = "".join(json_lines).strip()
            if raw:
                try:
                    payloads.append((timestamp, json.loads(raw)))
                except json.JSONDecodeError as e:
                    print(f"  [warn] Could not parse payload at {timestamp}: {e}", file=sys.stderr)
        else:
            i += 1

    return payloads


def summarise(ts: str, payload: dict) -> str:
    event = payload.get("event", "?")
    data = payload.get("data", {})
    remote_jid = data.get("key", {}).get("remoteJid", "?")
    msg_types = list(data.get("message", {}).keys())
    return f"{ts}  event={event}  from={remote_jid}  types={msg_types}"


def main():
    parser = argparse.ArgumentParser(description="Replay webhook payloads from daemon debug logs")
    parser.add_argument("log_file", help="Path to debug log file")
    parser.add_argument("--index", type=int, default=0, help="Replay payload at this index (0-based, default: 0)")
    parser.add_argument("--list", action="store_true", help="List payloads without replaying")
    parser.add_argument("--url", default=DAEMON_URL, help=f"Daemon URL (default: {DAEMON_URL})")
    args = parser.parse_args()

    payloads = extract_payloads(args.log_file)
    if not payloads:
        print("No payloads found in log file.")
        sys.exit(1)

    print(f"Found {len(payloads)} payload(s) in {args.log_file}:")
    for idx, (ts, payload) in enumerate(payloads):
        print(f"  [{idx}] {summarise(ts, payload)}")

    if args.list:
        return

    print()
    ts, payload = payloads[args.index]
    with httpx.Client(timeout=90) as client:
        print(f"→ Replaying [{args.index}] {ts} …")
        resp = client.post(f"{args.url}/webhook", json=payload)
        print(f"  HTTP {resp.status_code}  {resp.text[:300]}")


if __name__ == "__main__":
    main()
