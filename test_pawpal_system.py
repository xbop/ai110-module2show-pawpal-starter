from datetime import date, datetime, time, timedelta, timezone
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


def test_filter_tasks_by_completion_and_pet_name():
    walk = Task("Walk", 20, "daily")
    feed = Task("Feed", 5, "daily", completed=True)
    play = Task("Play", 10, "daily")
    first = Pet("Mochi", "dog", [walk, feed])
    second = Pet("mochi", "cat", [play])
    owner = Owner("Jordan", 60, pets=[first, second])
    scheduler = Scheduler(owner)
    assert scheduler.filter_tasks() == [(first, walk), (first, feed), (second, play)]
    assert scheduler.filter_tasks(completed=False) == [(first, walk), (second, play)]
    assert scheduler.filter_tasks(completed=True) == [(first, feed)]
    assert scheduler.filter_tasks(pet_name=" MOCHI ") == [
        (first, walk), (first, feed), (second, play)
    ]
    assert scheduler.filter_tasks(completed=True, pet_name="mochi") == [(first, feed)]
    assert scheduler.filter_tasks(pet_name="Luna") == []
    assert Scheduler(Owner("Empty", 0)).filter_tasks() == []
    with pytest.raises(ValueError):
        scheduler.filter_tasks(pet_name=" ")
    with pytest.raises(ValueError):
        scheduler.filter_tasks(completed=1)


def test_sort_by_time_is_stable_and_does_not_change_task_order():
    long = Task("Walk", 25, "daily")
    first_short = Task("Feed", 10, "daily", completed=True)
    second_short = Task("Play", 10, "daily")
    first = Pet("Mochi", "dog", [long, first_short])
    second = Pet("Luna", "cat", [second_short])
    owner = Owner("Jordan", 60, pets=[first, second])
    assert Scheduler(owner).sort_by_time() == [
        (first, first_short), (second, second_short), (first, long)
    ]
    assert first.tasks == [long, first_short]
    assert Scheduler(Owner("Empty", 0)).sort_by_time() == []


def test_detect_conflicts_across_and_within_pets():
    first = Pet("Mochi", "dog")
    second = Pet("Luna", "cat")
    scheduler = Scheduler(Owner("Jordan", 60, pets=[first, second]))
    start = datetime(2026, 1, 1, 9)

    def entry(pet, name, begin, end):
        return (pet, Task(name, 10, "once"), begin, end, "test")

    a = entry(first, "Walk", start, start + timedelta(minutes=30))
    b = entry(first, "Feed", start + timedelta(minutes=10), start + timedelta(minutes=20))
    c = entry(second, "Play", start + timedelta(minutes=25), start + timedelta(minutes=40))
    adjacent = entry(second, "Groom", start + timedelta(minutes=40), start + timedelta(minutes=50))
    skipped = entry(first, "Skipped", None, None)
    assert scheduler.detect_conflicts([a, b, c, adjacent, skipped]) == [
        "Schedule conflict: Mochi: Walk overlaps Mochi: Feed.",
        "Schedule conflict: Mochi: Walk overlaps Luna: Play.",
    ]
    assert scheduler.detect_conflicts([]) == []


def test_detect_conflicts_validates_intervals_and_generated_plan():
    pet = Pet("Mochi", "dog", [Task("Walk", 10, "once"), Task("Feed", 10, "once")])
    scheduler = Scheduler(Owner("Jordan", 60, pets=[pet]))
    assert scheduler.detect_conflicts(scheduler.build_plan(time(9))) == []
    start = datetime(2026, 1, 1, 9)
    task = pet.tasks[0]
    assert scheduler.detect_conflicts([(pet, task, start, None, "")]) == [
        "Cannot check Mochi: Walk: both start and end datetimes are required."
    ]
    assert scheduler.detect_conflicts([(pet, task, start, start, "")]) == [
        "Cannot check Mochi: Walk: end must be after start."
    ]
    assert scheduler.detect_conflicts([
        (pet, task, start, start + timedelta(minutes=10), ""),
        (pet, task, start.replace(tzinfo=timezone.utc),
         (start + timedelta(minutes=10)).replace(tzinfo=timezone.utc), ""),
    ]) == ["Cannot compare Mochi: Walk and Mochi: Walk: their timezones are incompatible."]
    assert scheduler.detect_conflicts([
        (pet, task, start, start.replace(tzinfo=timezone.utc), "")
    ]) == ["Cannot check Mochi: Walk: start and end use incompatible timezones."]
    utc = start.replace(tzinfo=timezone.utc)
    offset = timezone(timedelta(hours=1))
    later_zone = utc.astimezone(offset)
    first = (pet, task, utc, utc + timedelta(minutes=10), "")
    second = (pet, pet.tasks[1], later_zone, later_zone + timedelta(minutes=10), "")
    assert scheduler.detect_conflicts([first, second]) == [
        "Schedule conflict: Mochi: Walk overlaps Mochi: Feed."
    ]


def test_invalid_interval_does_not_hide_other_conflicts():
    pet = Pet("Mochi", "dog")
    task = Task("Walk", 10, "once")
    start = datetime(2026, 1, 1, 9)
    invalid = (pet, task, start, None, "")
    first = (pet, task, start, start + timedelta(minutes=10), "")
    second = (pet, Task("Feed", 5, "once"), start, start + timedelta(minutes=5), "")
    warnings = Scheduler(Owner("Jordan", 60)).detect_conflicts([invalid, first, second])
    assert len(warnings) == 2
    assert "Cannot check" in warnings[0]
    assert "overlaps" in warnings[1]


@pytest.mark.parametrize(("frequency", "days"), [("Daily", 1), ("weekly", 7)])
def test_completing_recurring_task_creates_one_future_occurrence(frequency, days):
    task = Task(
        "Walk", 20, frequency, priority="high", category="walk",
        due_date=date.today() - timedelta(days=5),
    )
    pet = Pet("Mochi", "dog", [task])
    next_task = task.mark_complete()
    assert next_task is not None
    assert task.completed
    assert next_task is not task
    assert next_task.due_date == date.today() + timedelta(days=days)
    assert (next_task.description, next_task.duration_minutes, next_task.frequency,
            next_task.priority, next_task.category, next_task.completed) == (
        "Walk", 20, frequency, "high", "walk", False
    )
    assert pet.tasks == [task, next_task]
    assert task.mark_complete() is next_task
    assert len(pet.tasks) == 2
    scheduler = Scheduler(Owner("Jordan", 60, pets=[pet]))
    assert scheduler.build_plan(time(9)) == []
    next_task.due_date = date.today()
    assert scheduler.build_plan(time(9))[0][1] is next_task


def test_reopening_removes_only_untouched_next_occurrence():
    task = Task("Feed", 5, "daily")
    pet = Pet("Mochi", "dog", [task])
    future = task.mark_complete()
    assert future is not None
    task.mark_incomplete()
    assert not task.completed and pet.tasks == [task]
    assert future._pet is None

    future = task.mark_complete()
    assert future is not None
    future.description = "Edited feed"
    task.mark_incomplete()
    assert pet.tasks == [task, future]
    assert task.mark_complete() is future
    assert len(pet.tasks) == 2
    future.mark_complete()
    task.mark_incomplete()
    assert future in pet.tasks
    assert future.completed


def test_unattached_and_nonrecurring_completion():
    task = Task("Walk", 10, "daily")
    future = task.mark_complete()
    assert future is not None
    pet = Pet("Luna", "dog")
    pet.add_task(task)
    assert pet.tasks == [task, future]
    task.mark_incomplete()
    assert pet.tasks == [task]
    once = Task("Vet visit", 30, "once")
    pet.add_task(once)
    assert once.mark_complete() is None
    assert pet.tasks == [task, once]


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
