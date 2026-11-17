"""Tests for the PawPal system."""

from pawpal_system import Pet, Task


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
