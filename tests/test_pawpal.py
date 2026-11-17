"""Tests for the PawPal system."""

from datetime import date, datetime, time, timedelta

from pawpal_system import Owner, Pet, Scheduler, Task


def test_mark_complete_changes_task_status():
    task = Task("Walk", 20, "daily")
    assert task.completed is False

    task.mark_complete()

    assert task.completed is True


def test_add_task_increases_pet_task_count():
    pet = Pet("Mochi", "dog")
    task = Task("Walk", 20, "daily")
    initial_count = len(pet.tasks)

    pet.add_task(task)

    assert len(pet.tasks) == initial_count + 1
    assert pet.tasks[-1] is task


def test_generated_schedule_is_in_chronological_order():
    pet = Pet("Mochi", "dog", [
        Task("Play", 15, "once", priority="low"),
        Task("Feed", 10, "once", priority="high"),
        Task("Walk", 20, "once", priority="medium"),
    ])
    plan = Scheduler(Owner("Jordan", 60, pets=[pet])).build_plan(time(9))

    assert [task.description for _, task, _, _, _ in plan] == ["Feed", "Walk", "Play"]
    assert [start.time() for _, _, start, _, _ in plan if start is not None] == [
        time(9), time(9, 10), time(9, 30)
    ]


def test_daily_completion_creates_task_due_tomorrow():
    task = Task("Feed", 10, "daily")
    pet = Pet("Mochi", "dog", [task])
    today = date.today()

    next_task = task.mark_complete()

    assert task.completed
    assert next_task is not None and next_task is not task
    assert next_task.due_date == today + timedelta(days=1)
    assert not next_task.completed
    assert pet.tasks == [task, next_task]


def test_scheduler_warns_when_tasks_have_the_same_start_time():
    first, second = Pet("Mochi", "dog"), Pet("Luna", "cat")
    start = datetime(2026, 1, 1, 9)
    plan = [
        (first, Task("Walk", 20, "once"), start, start + timedelta(minutes=20), ""),
        (second, Task("Feed", 10, "once"), start, start + timedelta(minutes=10), ""),
    ]

    warnings = Scheduler(Owner("Jordan", 60)).detect_conflicts(plan)

    assert warnings == ["Schedule conflict: Mochi: Walk overlaps Luna: Feed."]
