#!/usr/bin/env python3
"""CLI helper to inspect monitoring data produced by the stock market bots."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from monitoring import load_all_statuses


def parse_timestamp(raw: Optional[str]) -> Optional[datetime]:
    """Parse an ISO8601 timestamp stored in the monitoring files."""
    if not raw:
        return None
    cleaned = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def format_delta(delta) -> str:
    seconds = int(delta.total_seconds())
    if seconds < 0:
        seconds = 0
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h {minutes % 60}m"
    days = hours // 24
    return f"{days}d {hours % 24}h"


def describe_timestamp(raw: Optional[str], now: datetime) -> str:
    parsed = parse_timestamp(raw)
    if not parsed:
        return "never"
    parsed = parsed.astimezone(timezone.utc)
    return f"{parsed.strftime('%Y-%m-%d %H:%M:%S UTC')} ({format_delta(now - parsed)} ago)"


def dump_metadata(metadata: Any) -> Iterable[str]:
    if isinstance(metadata, dict) and metadata:
        json_blob = json.dumps(metadata, indent=2, sort_keys=True)
        for line in json_blob.splitlines():
            yield line


def render_status(state: Dict[str, Any], now: datetime, max_events: int) -> None:
    bot_name = state.get('bot_name', 'unknown bot')
    print(f"=== {bot_name} ===")
    print(f"Last success: {describe_timestamp(state.get('last_success'), now)}")
    print(f"Last failure: {describe_timestamp(state.get('last_failure'), now)}")
    print(
        f"Successes: {state.get('success_count', 0)} | Failures: {state.get('failure_count', 0)}"
    )

    runs = state.get('runs') or {}
    if runs:
        print("Last recorded runs:")
        for run_name in sorted(runs):
            run_info = runs[run_name]
            timestamp = describe_timestamp(run_info.get('timestamp'), now)
            status = run_info.get('status', 'unknown')
            message = run_info.get('message')
            print(f"  - {run_name}: {status} @ {timestamp}")
            if message:
                print(f"    {message}")
            for line in dump_metadata(run_info.get('metadata')):
                print(f"    {line}")
    else:
        print("No runs recorded yet.")

    events = state.get('events') or []
    if events:
        print(f"Recent events (last {min(len(events), max_events)} shown):")
        for event in events[-max_events:]:
            event_ts = describe_timestamp(event.get('timestamp'), now)
            event_type = event.get('type', 'info')
            message = event.get('message', '')
            print(f"  - [{event_type}] {event_ts}: {message}")
            for line in dump_metadata(event.get('metadata')):
                print(f"    {line}")
    else:
        print("No events recorded yet.")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Display monitoring information for the stock market bots.",
    )
    parser.add_argument(
        "--status-dir",
        default="monitoring",
        help="Directory containing <bot>_status.json files (default: monitoring)",
    )
    parser.add_argument(
        "--events",
        type=int,
        default=5,
        help="Number of recent events to show for each bot (default: 5)",
    )
    args = parser.parse_args()

    statuses = load_all_statuses(args.status_dir)
    if not statuses:
        print(f"No monitoring data found in {args.status_dir}.")
        return

    now = datetime.now(timezone.utc)
    for state in sorted(statuses, key=lambda item: item.get('bot_name', '')):
        render_status(state, now, max_events=max(1, args.events))


if __name__ == "__main__":
    main()
