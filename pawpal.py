"""Pet care models and a deterministic daily planner."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta


CATEGORIES = ("walk", "feeding", "medication", "enrichment", "grooming", "other")
PRIORITIES = ("high", "medium", "low")


@dataclass
class Owner:
    name: str
    available_minutes: int
    preferred_category: str = "none"

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("Owner name cannot be empty.")
        if not isinstance(self.available_minutes, int) or self.available_minutes < 0:
            raise ValueError("Available time must be a non-negative number of minutes.")
        if self.preferred_category not in ("none", *CATEGORIES):
            raise ValueError("Choose a valid preferred category.")


@dataclass
class Pet:
    name: str
    species: str
    owner: Owner

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.species = self.species.strip()
        if not self.name or not self.species:
            raise ValueError("Pet name and species cannot be empty.")


@dataclass
class CareTask:
    title: str
    category: str
    duration_minutes: int
    priority: str

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("Task title cannot be empty.")
        if self.category not in CATEGORIES:
            raise ValueError("Choose a valid task category.")
        if not isinstance(self.duration_minutes, int) or self.duration_minutes <= 0:
            raise ValueError("Task duration must be a positive number of minutes.")
        if self.priority not in PRIORITIES:
            raise ValueError("Choose a valid task priority.")


@dataclass
class DailyPlanner:
    pet: Pet
    tasks: list[CareTask]

    def build_plan(
        self, start_time: time
    ) -> list[tuple[CareTask, datetime | None, datetime | None, str]]:
        """Return each task with suggested times, or a reason it did not fit."""
        if start_time.second or start_time.microsecond or start_time.tzinfo:
            raise ValueError("Start time must be a local time rounded to a minute.")

        start = datetime.combine(datetime.today().date(), start_time)
        midnight = datetime.combine(start.date() + timedelta(days=1), time.min)
        available = min(
            self.pet.owner.available_minutes, int((midnight - start).total_seconds() // 60)
        )
        current = start
        ordered_tasks = sorted(
            self.tasks,
            key=lambda task: (
                PRIORITIES.index(task.priority),
                task.category != self.pet.owner.preferred_category,
            ),
        )
        plan = []
        for task in ordered_tasks:
            if task.duration_minutes > available:
                reason = (
                    f"Needs {task.duration_minutes} minutes; only {available} "
                    "minutes remain in today's available time."
                )
                plan.append((task, None, None, reason))
                continue

            end = current + timedelta(minutes=task.duration_minutes)
            reason = f"{task.priority.capitalize()} priority"
            if task.category == self.pet.owner.preferred_category:
                reason += "; matches your preferred category"
            reason += f"; fits in the remaining {available} minutes."
            plan.append((task, current, end, reason))
            current = end
            available -= task.duration_minutes
        return plan
