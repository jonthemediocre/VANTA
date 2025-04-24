"""Season‑aware Task System — skeleton implementation.

Matches Jon's request for Domain → Workspace → Task → SubTask hierarchy
with optional Season overlay for prioritization (+ money season).

Replace with full logic as needed.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

class Season(Enum):
    MONEY = "money"
    FAMILY = "family"
    HEALTH = "health"

@dataclass
class SubTask:
    title: str
    done: bool = False

@dataclass
class Task:
    title: str
    subtasks: List[SubTask] = field(default_factory=list)
    value_weight: float = 1.0

@dataclass
class Workspace:
    name: str
    tasks: List[Task] = field(default_factory=list)

@dataclass
class Domain:
    name: str
    workspaces: List[Workspace] = field(default_factory=list)

class TaskManager:
    def __init__(self, season: Season = Season.MONEY):
        self.season = season
        self.domains: List[Domain] = []

    def prioritize(self):
        # basic prioritization: sort by value_weight * season_factor
        factor = {
            Season.MONEY: 1.5,
            Season.FAMILY: 1.2,
            Season.HEALTH: 1.0,
        }[self.season]
        for domain in self.domains:
            for ws in domain.workspaces:
                ws.tasks.sort(key=lambda t: t.value_weight * factor, reverse=True)
        return self

    def report_next(self):
        self.prioritize()
        for domain in self.domains:
            for ws in domain.workspaces:
                if ws.tasks:
                    return domain.name, ws.name, ws.tasks[0].title
        return None

if __name__ == "__main__":
    # quick smoke test
    mgr = TaskManager()
    mgr.domains.append(
        Domain(
            "Sales",
            [Workspace("Pipeline", [Task("Call Macy's buyer", value_weight=3.0)])],
        )
    )
    print("Next task:", mgr.report_next())
