from datetime import time, timedelta, timezone
from unittest.mock import patch

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task


def test_owner_collects_tasks_for_all_pets_including_completed():
    walk = Task("Walk", 20, "daily")
    feed = Task("Feed", 5, "daily", completed=True)
    owner = Owner("Jordan", 30, pets=[
        Pet("Mochi", "dog", [walk]),
        Pet("Luna", "cat", [feed]),
    ])
    assert owner.get_all_tasks() == [(owner.pets[0], walk), (owner.pets[1], feed)]


def test_scheduler_uses_owner_tasks_and_orders_across_pets():
    owner = Owner("Jordan", 30, preferred_category="walk")
    first, second = Pet("Mochi", "dog"), Pet("Luna", "cat")
    first.add_task(Task("Feed", 10, "daily", priority="high", category="feeding"))
    second.add_task(Task("Walk", 20, "daily", priority="high", category="walk"))
    second.add_task(Task("Groom", 10, "weekly", priority="low"))
    owner.add_pet(first)
    owner.add_pet(second)

    with patch.object(owner, "get_all_tasks", wraps=owner.get_all_tasks) as get_tasks:
        plan = Scheduler(owner).build_plan(time(9))
    get_tasks.assert_called_once_with()
    assert [item[1].description for item in plan] == ["Walk", "Feed", "Groom"]
    assert [item[0].name for item in plan] == ["Luna", "Mochi", "Luna"]
    assert plan[0][2].time() == time(9)
    assert plan[1][3].time() == time(9, 30)
    assert "matches your preferred category" in plan[0][4]
    assert plan[2][2] is None
    assert "only 0 minutes remain" in plan[2][4]


def test_skips_long_tasks_and_completed_tasks_and_can_reset_status():
    long = Task("Groom", 31, "weekly", priority="high")
    done = Task("Feed", 5, "daily", completed=True)
    short = Task("Play", 10, "daily")
    owner = Owner("Jordan", 10, pets=[Pet("Mochi", "dog", [long, done, short])])
    scheduler = Scheduler(owner)
    plan = scheduler.build_plan(time(9))
    assert [(item[1].description, item[2] is not None) for item in plan] == [
        ("Groom", False), ("Play", True)
    ]
    short.mark_complete()
    done.mark_incomplete()
    assert [item[1].description for item in scheduler.build_plan(time(9))] == [
        "Groom", "Feed"
    ]


def test_empty_lists_are_independent_and_midnight_limits_plan():
    first, second = Pet("Mochi", "dog"), Pet("Luna", "cat")
    first.add_task(Task("Walk", 10, "daily"))
    assert second.tasks == []
    owner = Owner("Jordan", 60, pets=[first, second])
    assert Owner("Other", 0).pets == []
    plan = Scheduler(owner).build_plan(time(23, 50))
    assert plan[0][3].time() == time(0)
    assert plan[0][3].date() == plan[0][2].date() + timedelta(days=1)
    assert Scheduler(Owner("Empty", 10)).build_plan(time(9)) == []


@pytest.mark.parametrize(
    "factory",
    [
        lambda: Task(" ", 5, "daily"),
        lambda: Task("Feed", 0, "daily"),
        lambda: Task("Feed", True, "daily"),
        lambda: Task("Feed", 5, ""),
        lambda: Task("Feed", 5, "daily", completed="yes"),
        lambda: Task("Feed", 5, "daily", priority="urgent"),
        lambda: Pet("", "cat"),
        lambda: Owner("Jordan", -1),
        lambda: Scheduler(Owner("Jordan", 5)).build_plan(time(9, 0, 1)),
        lambda: Scheduler(Owner("Jordan", 5)).build_plan(time(9, tzinfo=timezone.utc)),
    ],
)
def test_invalid_values_raise_errors(factory):
    with pytest.raises(ValueError):
        factory()
