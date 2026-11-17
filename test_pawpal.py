from datetime import time, timedelta, timezone

import pytest

from pawpal import CareTask, DailyPlanner, Owner, Pet


def task(title, minutes, priority="medium", category="other"):
    return CareTask(title, category, minutes, priority)


def planner(tasks, minutes=60, preference="none"):
    owner = Owner("Jordan", minutes, preference)
    return DailyPlanner(Pet("Mochi", "dog", owner), tasks)


def test_pets_can_share_an_owner_and_planner_uses_that_owner():
    owner = Owner("Jordan", 5, "walk")
    first = Pet("Mochi", "dog", owner)
    second = Pet("Luna", "cat", owner)
    assert first.owner is second.owner
    plan = DailyPlanner(first, [task("walk", 5, category="walk")]).build_plan(time(9))
    assert plan[0][1] is not None
    assert "matches your preferred category" in plan[0][3]


def test_priority_preference_and_stable_order():
    tasks = [
        task("low preferred", 5, "low", "walk"),
        task("high other", 5, "high"),
        task("high walk 1", 5, "high", "walk"),
        task("high walk 2", 5, "high", "walk"),
    ]
    plan = planner(tasks, preference="walk").build_plan(time(9))
    assert [item[0].title for item in plan] == [
        "high walk 1", "high walk 2", "high other", "low preferred"
    ]
    assert "matches your preferred category" in plan[0][3]
    assert plan[0][1].time() == time(9)
    assert plan[-1][2].time() == time(9, 20)


def test_skips_task_that_does_not_fit_and_continues():
    plan = planner(
        [task("long", 31, "high"), task("short", 20, "medium"), task("last", 10, "low")],
        minutes=30,
    ).build_plan(time(10))
    assert plan[0][1] is None
    assert "only 30 minutes remain" in plan[0][3]
    assert plan[1][1].time() == time(10)
    assert plan[2][2].time() == time(10, 30)


def test_midnight_and_zero_time_limits():
    plan = planner([task("late", 11), task("fits", 10)], minutes=60).build_plan(time(23, 50))
    assert plan[0][1] is None
    assert plan[1][2].time() == time(0)
    assert plan[1][2].date() == plan[1][1].date() + timedelta(days=1)
    assert planner([task("walk", 1)], minutes=0).build_plan(time(9))[0][1] is None
    assert planner([]).build_plan(time(9)) == []


@pytest.mark.parametrize(
    "factory",
    [
        lambda: Owner(" ", 10),
        lambda: Owner("Jordan", -1),
        lambda: Owner("Jordan", 10, "unknown"),
        lambda: Pet("", "dog", Owner("Jordan", 10)),
        lambda: task("", 10),
        lambda: task("walk", 0),
        lambda: task("walk", 10, "urgent"),
        lambda: task("walk", 10, category="unknown"),
        lambda: planner([]).build_plan(time(9, 0, 1)),
        lambda: planner([]).build_plan(time(9, tzinfo=timezone.utc)),
    ],
)
def test_invalid_inputs_are_rejected(factory):
    with pytest.raises(ValueError):
        factory()
