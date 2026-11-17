"""UML-based skeleton for the PawPal+ logic layer."""

from dataclasses import dataclass
from datetime import datetime, time


@dataclass
class Owner:
    name: str
    available_minutes: int
    preferred_category: str = "none"


@dataclass
class Pet:
    name: str
    species: str
    owner: Owner


@dataclass
class CareTask:
    title: str
    category: str
    duration_minutes: int
    priority: str


@dataclass
class DailyPlanner:
    pet: Pet
    tasks: list[CareTask]

    def build_plan(
        self, start_time: time
    ) -> list[tuple[CareTask, datetime | None, datetime | None, str]]:
        raise NotImplementedError("Daily planning has not been implemented in this skeleton.")
