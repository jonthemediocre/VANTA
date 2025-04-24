
# ---
# module: vanta.upgrades
# version: 0.1.0
# description: "Trace‑logging, watchdog recovery, roadmap planning and memory GC for the VANTA Modular Agentic FrAmEwOrK."
# author: ChatGPT‑VANTA
# dependencies:
#   - python>=3.10
# ---

"""
Adds two core capabilities:

2️⃣  Trace‑Logger + WatchdogSupervisor  →  transparency & automatic recovery
5️⃣  RoadmapPlanner + MemoryGC         →  long‑term coherence & lean recall
"""

from __future__ import annotations

import datetime as _dt
import json as _json
import logging as _logging
import os as _os
import time as _time
import traceback as _tb
import uuid as _uuid
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List

###############################################################################
# 2️⃣  TRACE‑LOGGER ############################################################
###############################################################################

def _default_log_dir() -> Path:
    return Path(_os.getenv("VANTA_LOG_DIR", "./logs")).resolve()

def trace_logger(step_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that wraps a function and appends a JSONL record to a per‑session
    log file. Session id can be passed via kwargs or auto‑generated."""
    def _decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def _wrapper(*args: Any, **kwargs: Any):
            session_id: str = kwargs.get("session_id", str(_uuid.uuid4()))
            log_file = _default_log_dir() / f"{session_id}.jsonl"
            log_file.parent.mkdir(parents=True, exist_ok=True)
            start = _time.perf_counter()
            entry: Dict[str, Any] = {
                "ts": _dt.datetime.utcnow().isoformat() + "Z",
                "step": step_name,
                "fn": func.__name__,
                "args_preview": str(args)[:120],
                "kwargs_preview": str(kwargs)[:120],
            }
            try:
                result = func(*args, **kwargs)
                entry.update({
                    "status": "ok",
                    "rt_ms": int((_time.perf_counter() - start) * 1000),
                })
                return result
            except Exception as exc:
                entry.update({
                    "status": "error",
                    "rt_ms": int((_time.perf_counter() - start) * 1000),
                    "error": type(exc).__name__,
                    "msg": str(exc),
                    "traceback": _tb.format_exc(limit=5),
                })
                raise
            finally:
                with open(log_file, "a", encoding="utf-8") as fh:
                    fh.write(_json.dumps(entry) + "\n")
        return _wrapper
    return _decorator

###############################################################################
# 2️⃣  WATCHDOG SUPERVISOR #####################################################
###############################################################################
@dataclass
class WatchdogSupervisor:
    """Runs a callable with a timeout and automatic retry."""

    timeout_s: int = 30
    retries: int = 1

    def run(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        import threading, queue as _queue
        attempt = 0
        while attempt <= self.retries:
            q: _queue.Queue = _queue.Queue(maxsize=1)
            def _target():
                try:
                    q.put((True, fn(*args, **kwargs)), block=False)
                except Exception as exc:  # noqa: BLE001
                    q.put((False, exc), block=False)

            t = threading.Thread(target=_target, daemon=True)
            t.start()
            t.join(self.timeout_s)

            if t.is_alive():
                _logging.warning("Watchdog: timeout >%s s in %s (attempt %s)",
                                 self.timeout_s, fn.__name__, attempt)
                attempt += 1
                continue

            success, val = q.get()
            if success:
                return val
            _logging.warning("Watchdog: error in %s – %s", fn.__name__, val)
            attempt += 1
        raise RuntimeError(f"Watchdog: {fn.__name__} failed after {self.retries + 1} attempts")

###############################################################################
# 5️⃣  ROADMAP PLANNER #########################################################
###############################################################################
@dataclass
class Milestone:
    id: str
    title: str
    due: _dt.date | None = None
    status: str = "todo"  # todo | in‑progress | done | blocked

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "due": self.due.isoformat() if self.due else None,
            "status": self.status,
        }

@dataclass
class RoadmapPlanner:
    """Lightweight project‑graph manager persisted to JSON."""
    path: Path | str
    _data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.path = Path(self.path)
        if self.path.exists():
            self._data = _json.loads(self.path.read_text())

    def add_goal(self, goal: str, milestones: List[Milestone] | None = None):
        if goal in self._data:
            raise ValueError(f"Roadmap goal '{goal}' already exists")
        self._data[goal] = {
            "created": _dt.date.today().isoformat(),
            "milestones": [m.to_dict() for m in (milestones or [])],
        }
        self._flush()

    def update_status(self, goal: str, milestone_id: str, new_status: str):
        goal_node = self._data.get(goal)
        if not goal_node:
            raise KeyError(goal)
        for m in goal_node["milestones"]:
            if m["id"] == milestone_id:
                m["status"] = new_status
                self._flush()
                return
        raise KeyError(milestone_id)

    def _flush(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(_json.dumps(self._data, indent=2))

###############################################################################
# 5️⃣  MEMORY GC ###############################################################
###############################################################################
@dataclass
class MemoryGC:
    """Garbage‑collects JSONL memory files based on recency × utility."""

    path: Path | str
    recency_halflife_days: float = 14.0
    utility_weight: float = 0.6
    keep_top_n: int = 5000  # surface memory size

    def run_gc(self):
        store_path = Path(self.path)
        cold_path = store_path / "cold"
        cold_path.mkdir(parents=True, exist_ok=True)
        scored: List[tuple[float, Path]] = []
        for p in store_path.glob("*.jsonl"):
            with open(p, "r", encoding="utf-8") as fh:
                for line in fh:
                    rec = _json.loads(line)
                    age_days = ( _dt.datetime.utcnow() -
                                 _dt.datetime.fromisoformat(rec["recency"]) ).days
                    recency_score = 0.5 ** (age_days / self.recency_halflife_days)
                    total_score = (1 - self.utility_weight) * recency_score + \
                                  self.utility_weight * rec["utility"]
                    scored.append((total_score, p))
        scored.sort(reverse=True)
        for i, (_, path) in enumerate(scored):
            if i >= self.keep_top_n and path.exists():
                new_loc = cold_path / path.name
                path.replace(new_loc)
