"""Monitoring utilities for the stock market bots.

This module provides a lightweight monitoring helper that persists
structured status information to JSON files. The monitor tracks the most
recent runs, aggregates success and failure counts, and stores a short
history of notable events. Data is written atomically so the files can be
safely tailed or inspected by other processes.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class BotMonitor:
    """Persist simple status information for a bot run."""

    def __init__(
        self,
        bot_name: str,
        status_dir: str = "monitoring",
        max_events: int = 50,
    ) -> None:
        self.bot_name = bot_name
        self.status_dir = Path(status_dir)
        self.status_file = self.status_dir / f"{bot_name}_status.json"
        self.max_events = max_events
        self._lock = threading.Lock()

        # Ensure the monitoring directory exists.
        try:
            self.status_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logging.error("Could not create monitoring directory %s: %s", self.status_dir, exc)

        self._state: Dict[str, Any] = self._load_state()

    # ------------------------------------------------------------------
    def _load_state(self) -> Dict[str, Any]:
        """Load existing monitoring state from disk."""
        if self.status_file.exists():
            try:
                with self.status_file.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if isinstance(data, dict):
                    return self._apply_defaults(data)
            except (json.JSONDecodeError, OSError) as exc:
                logging.warning(
                    "Could not read monitoring state from %s: %s", self.status_file, exc
                )
        return self._apply_defaults({})

    def _apply_defaults(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure required keys exist in the monitoring state."""
        state.setdefault("bot_name", self.bot_name)
        state.setdefault("last_updated", None)
        state.setdefault("last_success", None)
        state.setdefault("last_failure", None)
        state.setdefault("success_count", 0)
        state.setdefault("failure_count", 0)
        state.setdefault("events", [])
        state.setdefault("runs", {})
        return state

    def _save_state(self) -> None:
        """Persist monitoring state atomically."""
        tmp_path = self.status_file.with_suffix(".tmp")
        try:
            with tmp_path.open("w", encoding="utf-8") as handle:
                json.dump(self._state, handle, indent=2)
            os.replace(tmp_path, self.status_file)
        except OSError as exc:
            logging.error("Failed to write monitoring state to %s: %s", self.status_file, exc)

    def _record_event_locked(
        self,
        timestamp: str,
        event_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]],
    ) -> None:
        event: Dict[str, Any] = {
            "timestamp": timestamp,
            "type": event_type,
            "message": message,
        }
        if metadata:
            event["metadata"] = metadata

        events: List[Dict[str, Any]] = self._state.setdefault("events", [])
        events.append(event)
        if len(events) > self.max_events:
            events = events[-self.max_events :]
        self._state["events"] = events

        self._state["last_updated"] = timestamp
        if event_type == "success":
            self._state["last_success"] = timestamp
            self._state["success_count"] = self._state.get("success_count", 0) + 1
        elif event_type == "error":
            self._state["last_failure"] = timestamp
            self._state["failure_count"] = self._state.get("failure_count", 0) + 1

    def record_event(
        self,
        event_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a generic monitoring event."""
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._record_event_locked(timestamp, event_type, message, metadata)
            self._save_state()

    def record_run(
        self,
        run_type: str,
        status: str,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record the outcome of a scheduled run."""
        timestamp = datetime.now(timezone.utc).isoformat()
        run_entry: Dict[str, Any] = {
            "status": status,
            "timestamp": timestamp,
        }
        if message:
            run_entry["message"] = message
        if metadata:
            run_entry["metadata"] = metadata

        with self._lock:
            runs: Dict[str, Any] = self._state.setdefault("runs", {})
            runs[run_type] = run_entry

            if status == "success":
                event_type = "success"
            elif status == "error":
                event_type = "error"
            elif status == "warning":
                event_type = "warning"
            else:
                event_type = "info"

            default_message = f"{run_type} run reported {status}"
            self._record_event_locked(
                timestamp,
                event_type,
                message or default_message,
                metadata,
            )
            self._save_state()

    def get_state(self) -> Dict[str, Any]:
        """Return a deep copy of the current monitoring state."""
        with self._lock:
            # Using JSON round-trip to create a deep copy without external deps.
            return json.loads(json.dumps(self._state))


def load_all_statuses(status_dir: str = "monitoring") -> List[Dict[str, Any]]:
    """Load the monitoring state for every tracked bot."""
    status_path = Path(status_dir)
    if not status_path.exists() or not status_path.is_dir():
        return []

    statuses: List[Dict[str, Any]] = []
    for file_path in sorted(status_path.glob("*_status.json")):
        try:
            with file_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                statuses.append(data)
        except (json.JSONDecodeError, OSError) as exc:
            logging.warning("Could not read monitoring file %s: %s", file_path, exc)
    return statuses


__all__ = ["BotMonitor", "load_all_statuses"]
