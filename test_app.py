from datetime import date, timedelta
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from pawpal import CareTask
from pawpal_system import Owner, Pet, Scheduler, Task


def element(elements, label):
    return next(item for item in elements if item.label == label)


def add_pet(app, name, species):
    element(app.text_input, "Pet name").input(name)
    element(app.text_input, "Species").input(species)
    element(app.button, "Add pet").click().run()


def add_task(app, name, duration=20, category="walk"):
    element(app.text_input, "Task title").input(name)
    element(app.number_input, "Duration (minutes)").set_value(duration)
    element(app.selectbox, "Category").select(category)
    element(app.button, "Add task").click().run()


def test_multi_pet_owner_persists_across_reruns():
    app = AppTest.from_file("app.py", default_timeout=30).run()
    owner = app.session_state.owner
    assert isinstance(owner, Owner)
    pet = Pet("Luna", "cat")
    task = Task("Play", 15, "daily")
    pet.add_task(task)
    owner.add_pet(pet)
    element(app.text_input, "Owner name").input("Alex").run()
    assert app.session_state.owner is owner
    assert app.session_state.owner.get_all_tasks() == [(pet, task)]
    assert not app.exception


def test_add_edit_schedule_and_remove_task():
    app = AppTest.from_file("app.py", default_timeout=30).run()
    add_pet(app, "Mochi", "dog")
    add_task(app, "Morning walk")
    pet = app.session_state.owner.pets[0]
    assert pet.tasks[0].description == "Morning walk"
    element(app.text_input, "Edit task title").input("Evening walk")
    element(app.number_input, "Edit duration (minutes)").set_value(35)
    element(app.button, "Save changes").click().run()
    assert pet.tasks[0].description == "Evening walk"
    assert pet.tasks[0].duration_minutes == 35
    element(app.button, "Generate schedule").click().run()
    assert any("Mochi: Evening walk" in item.value for item in app.markdown)
    element(app.button, "Remove selected task").click().run()
    assert not pet.tasks
    assert not app.exception


def test_multiple_pets_share_budget_and_completed_tasks_are_excluded():
    app = AppTest.from_file("app.py", default_timeout=30).run()
    add_pet(app, "Mochi", "dog")
    add_task(app, "Feed", category="feeding")
    add_pet(app, "Luna", "cat")
    element(app.selectbox, "Pet for this task").select(1).run()
    add_task(app, "Walk")
    element(app.number_input, "Time available today (minutes)").set_value(20)
    element(app.selectbox, "Preferred task category").select("walk")
    element(app.button, "Generate schedule").click().run()
    assert any("Luna: Walk" in item.value for item in app.markdown)
    assert any("Mochi: Feed" in item.value for item in app.markdown)
    assert any("matches your preferred category" in item.value for item in app.caption)

    element(app.checkbox, "Completed").check()
    element(app.button, "Save changes").click().run()
    element(app.button, "Generate schedule").click().run()
    assert any("Mochi: Feed" in item.value for item in app.markdown)
    assert not any("Luna: Walk" in item.value for item in app.markdown)
    assert not app.exception


def test_validation_and_legacy_tasks_migration():
    app = AppTest.from_file("app.py", default_timeout=30)
    app.session_state["tasks"] = [CareTask("Old walk", "walk", 15, "high")]
    app.run()
    assert any("previous single-pet session" in item.value for item in app.info)
    add_pet(app, "Mochi", "dog")
    assert app.session_state.owner.pets[0].tasks[0].description == "Old walk"
    assert "tasks" not in app.session_state
    element(app.text_input, "Task title").input(" ")
    element(app.button, "Add task").click().run()
    assert any("Description" in item.value for item in app.error)
    element(app.text_input, "Owner name").input(" ")
    element(app.button, "Generate schedule").click().run()
    assert any("Owner name" in item.value for item in app.error)


def test_all_completed_tasks_and_empty_owner_are_reported():
    app = AppTest.from_file("app.py", default_timeout=30).run()
    element(app.button, "Generate schedule").click().run()
    assert any("Add at least one task" in item.value for item in app.warning)
    add_pet(app, "Mochi", "dog")
    add_task(app, "Walk")
    element(app.checkbox, "Completed").check()
    element(app.button, "Save changes").click().run()
    pet = app.session_state.owner.pets[0]
    assert len(pet.tasks) == 2
    assert pet.tasks[1].due_date == date.today() + timedelta(days=1)
    element(app.button, "Generate schedule").click().run()
    assert any("No incomplete tasks are due today" in item.value for item in app.info)
    element(app.checkbox, "Completed").uncheck()
    element(app.button, "Save changes").click().run()
    assert len(pet.tasks) == 1
    assert not pet.tasks[0].completed


def test_schedule_displays_conflict_warning():
    app = AppTest.from_file("app.py", default_timeout=30).run()
    add_pet(app, "Mochi", "dog")
    add_task(app, "Walk")
    with patch.object(Scheduler, "detect_conflicts", return_value=["Schedule conflict: example."]):
        element(app.button, "Generate schedule").click().run()
    assert any("Schedule conflict: example." in item.value for item in app.warning)
    assert any("Mochi: Walk" in item.value for item in app.markdown)
    assert not app.exception
