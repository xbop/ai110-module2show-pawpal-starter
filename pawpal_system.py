"""Multi-pet care models and a priority-based daily scheduler."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta


PRIORITIES = ("high", "medium", "low")


@dataclass
class Task:
    description: str
    duration_minutes: int
    frequency: str
    completed: bool = False
    priority: str = "medium"
    category: str = "other"
    due_date: date = field(default_factory=date.today)
    _pet: Pet | None = field(default=None, init=False, repr=False, compare=False)
    _next: Task | None = field(default=None, init=False, repr=False, compare=False)
    _next_snapshot: tuple[str, int, str, str, str, date, bool] | None = field(
        default=None, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        """Normalize and validate task details."""
        self.description = self.description.strip()
        self.frequency = self.frequency.strip()
        self.category = self.category.strip()
        if not self.description or not self.frequency or not self.category:
            raise ValueError("Description, frequency, and category cannot be empty.")
        if type(self.duration_minutes) is not int or self.duration_minutes <= 0:
            raise ValueError("Task duration must be a positive number of minutes.")
        if not isinstance(self.completed, bool):
            raise ValueError("Completion status must be a boolean.")
        if self.priority not in PRIORITIES:
            raise ValueError("Priority must be high, medium, or low.")
        if type(self.due_date) is not date:
            raise ValueError("Due date must be a date.")

    def _details(self) -> tuple[str, int, str, str, str, date, bool]:
        """Return fields used to detect changes to a future occurrence."""
        return (
            self.description, self.duration_minutes, self.frequency, self.priority,
            self.category, self.due_date, self.completed,
        )

    def mark_complete(self) -> Task | None:
        """Complete once and return the next daily/weekly occurrence due from today, if any."""
        if self.completed:
            return self._next
        days = {"daily": 1, "weekly": 7}.get(self.frequency.casefold())
        if days is not None and self._next is None:
            next_task = Task(
                self.description, self.duration_minutes, self.frequency,
                priority=self.priority, category=self.category,
                due_date=date.today() + timedelta(days=days),
            )
            if self._pet is not None:
                self._pet.add_task(next_task)
            self._next = next_task
            self._next_snapshot = next_task._details()
        self.completed = True
        return self._next

    def mark_incomplete(self) -> None:
        """Reopen the task, removing its next occurrence only if it is untouched."""
        if self._next is not None and self._next._details() == self._next_snapshot:
            if self._pet is not None and self._next._pet is self._pet:
                self._pet.remove_task(self._next)
            self._next = None
            self._next_snapshot = None
        self.completed = False


@dataclass
class Pet:
    name: str
    species: str
    tasks: list[Task] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Normalize and validate pet details."""
        self.name = self.name.strip()
        self.species = self.species.strip()
        if not self.name or not self.species:
            raise ValueError("Pet name and species cannot be empty.")
        tasks = self.tasks
        self.tasks = []
        for task in tasks:
            self.add_task(task)

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet."""
        if task._pet is not None:
            raise ValueError("Task already belongs to a pet.")
        if (
            task._next is not None
            and task._next._pet is not None
            and task._next._pet is not self
        ):
            raise ValueError("The task's next occurrence belongs to another pet.")
        task._pet = self
        self.tasks.append(task)
        if task._next is not None and task._next._pet is None:
            self.add_task(task._next)

    def remove_task(self, task: Task) -> None:
        """Remove a task from this pet without removing its other occurrences."""
        for index, existing in enumerate(self.tasks):
            if existing is task:
                self.tasks.pop(index)
                task._pet = None
                for other in self.tasks:
                    if other._next is task:
                        other._next = None
                        other._next_snapshot = None
                return
        raise ValueError("Task does not belong to this pet.")


@dataclass
class Owner:
    name: str
    available_minutes: int
    preferred_category: str = "none"
    pets: list[Pet] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Normalize and validate owner details and available time."""
        self.name = self.name.strip()
        self.preferred_category = self.preferred_category.strip()
        if not self.name or not self.preferred_category:
            raise ValueError("Owner name and preferred category cannot be empty.")
        if type(self.available_minutes) is not int or self.available_minutes < 0:
            raise ValueError("Available time must be a non-negative number of minutes.")

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        self.pets.append(pet)

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        """Return each task alongside its pet, including completed tasks."""
        return [(pet, task) for pet in self.pets for task in pet.tasks]


@dataclass
class Scheduler:
    owner: Owner

    def detect_conflicts(
        self, plan: list[tuple[Pet, Task, datetime | None, datetime | None, str]]
    ) -> list[str]:
        """Warn about overlapping or invalid intervals; adjacent and unscheduled entries do not conflict."""
        scheduled = []
        warnings = []
        for entry in plan:
            pet, task, start, end, _ = entry
            label = f"{pet.name}: {task.description}"
            if start is None and end is None:
                continue
            if not isinstance(start, datetime) or not isinstance(end, datetime):
                warnings.append(
                    f"Cannot check {label}: both start and end datetimes are required."
                )
                continue
            start_aware = start.utcoffset() is not None
            end_aware = end.utcoffset() is not None
            if start_aware != end_aware:
                warnings.append(f"Cannot check {label}: start and end use incompatible timezones.")
                continue
            if end <= start:
                warnings.append(f"Cannot check {label}: end must be after start.")
                continue
            scheduled.append((label, start, end, start_aware))
        for index, (first_label, first_start, first_end, first_aware) in enumerate(scheduled):
            for second_label, second_start, second_end, second_aware in scheduled[index + 1:]:
                if first_aware != second_aware:
                    warnings.append(
                        f"Cannot compare {first_label} and {second_label}: "
                        "their timezones are incompatible."
                    )
                elif first_start < second_end and second_start < first_end:
                    warnings.append(f"Schedule conflict: {first_label} overlaps {second_label}.")
        return warnings

    def sort_by_time(self) -> list[tuple[Pet, Task]]:
        """Return all pet-task pairs ordered by duration, shortest first."""
        return sorted(self.owner.get_all_tasks(), key=lambda item: item[1].duration_minutes)

    def filter_tasks(
        self, completed: bool | None = None, pet_name: str | None = None
    ) -> list[tuple[Pet, Task]]:
        """Filter pet-task pairs by completion and/or case-insensitive exact pet name."""
        if completed is not None and not isinstance(completed, bool):
            raise ValueError("Completion filter must be a boolean or None.")
        if pet_name is not None:
            pet_name = pet_name.strip()
            if not pet_name:
                raise ValueError("Pet name filter cannot be empty.")
            pet_name = pet_name.casefold()
        return [
            (pet, task)
            for pet, task in self.owner.get_all_tasks()
            if (completed is None or task.completed == completed)
            and (pet_name is None or pet.name.casefold() == pet_name)
        ]

    def build_plan(
        self, start_time: time
    ) -> list[tuple[Pet, Task, datetime | None, datetime | None, str]]:
        """Schedule due tasks by priority and preference within today's available time."""
        if start_time.second or start_time.microsecond or start_time.tzinfo:
            raise ValueError("Start time must be a local time rounded to a minute.")

        start = datetime.combine(datetime.today().date(), start_time)
        midnight = datetime.combine(start.date() + timedelta(days=1), time.min)
        available = min(
            self.owner.available_minutes, int((midnight - start).total_seconds() // 60)
        )
        current = start
        pending = [
            item for item in self.filter_tasks(completed=False)
            if item[1].due_date <= start.date()
        ]
        pending.sort(
            key=lambda item: (
                PRIORITIES.index(item[1].priority),
                item[1].category != self.owner.preferred_category,
            )
        )
        plan = []
        for pet, task in pending:
            if task.duration_minutes > available:
                reason = (
                    f"Needs {task.duration_minutes} minutes; only {available} "
                    "minutes remain in today's available time."
                )
                plan.append((pet, task, None, None, reason))
                continue
            end = current + timedelta(minutes=task.duration_minutes)
            reason = f"{task.priority.capitalize()} priority"
            if task.category == self.owner.preferred_category:
                reason += "; matches your preferred category"
            reason += f"; fits in the remaining {available} minutes."
            plan.append((pet, task, current, end, reason))
            current = end
            available -= task.duration_minutes
        return plan
