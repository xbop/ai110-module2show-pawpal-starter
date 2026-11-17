"""Multi-pet care models and a priority-based daily scheduler."""

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta


PRIORITIES = ("high", "medium", "low")


@dataclass
class Task:
    description: str
    duration_minutes: int
    frequency: str
    completed: bool = False
    priority: str = "medium"
    category: str = "other"

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

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def mark_incomplete(self) -> None:
        """Mark this task as incomplete."""
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

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet."""
        self.tasks.append(task)


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

    def build_plan(
        self, start_time: time
    ) -> list[tuple[Pet, Task, datetime | None, datetime | None, str]]:
        """Schedule incomplete tasks or explain why they do not fit today."""
        if start_time.second or start_time.microsecond or start_time.tzinfo:
            raise ValueError("Start time must be a local time rounded to a minute.")

        start = datetime.combine(datetime.today().date(), start_time)
        midnight = datetime.combine(start.date() + timedelta(days=1), time.min)
        available = min(
            self.owner.available_minutes, int((midnight - start).total_seconds() // 60)
        )
        current = start
        pending = [item for item in self.owner.get_all_tasks() if not item[1].completed]
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
