from datetime import time

import streamlit as st

from pawpal import CATEGORIES
from pawpal_system import PRIORITIES, Owner, Pet, Scheduler, Task


st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.write("Make a practical care plan for your pets, based on the time you have.")

if "owner" not in st.session_state:
    st.session_state.owner = Owner("Jordan", available_minutes=60)
if "edit_version" not in st.session_state:
    st.session_state.edit_version = 0
owner = st.session_state.owner

st.subheader("Owner and planning preferences")
owner_name = st.text_input("Owner name", value=owner.name, key="owner_name")
available_minutes = st.number_input(
    "Time available today (minutes)",
    min_value=0,
    max_value=1440,
    value=owner.available_minutes,
    key="available_minutes",
)
start_time = st.time_input("Start time", value=time(9, 0), step=60)
preferred_category = st.selectbox(
    "Preferred task category",
    ("none", *CATEGORIES),
    index=("none", *CATEGORIES).index(owner.preferred_category),
    format_func=str.capitalize,
    key="preferred_category",
)
st.caption("Preference breaks ties between tasks of the same priority.")

st.subheader("Pets")
legacy_tasks = st.session_state.get("tasks", [])
if legacy_tasks:
    st.info("Tasks from the previous single-pet session will be assigned to the next pet you add.")
with st.form("add_pet", clear_on_submit=True):
    pet_name = st.text_input("Pet name", value="Mochi")
    species = st.text_input("Species", value="dog")
    if st.form_submit_button("Add pet"):
        try:
            pet = Pet(pet_name, species)
            for old_task in legacy_tasks:
                pet.add_task(
                    Task(
                        old_task.title,
                        old_task.duration_minutes,
                        "unspecified",
                        priority=old_task.priority,
                        category=old_task.category,
                    )
                )
        except ValueError as exc:
            st.error(str(exc))
        else:
            owner.add_pet(pet)
            if legacy_tasks:
                del st.session_state["tasks"]
            st.rerun()

st.subheader("Care tasks")
st.caption("Daily and weekly tasks create a new occurrence when completed.")
if owner.pets:
    pet_labels = [f"{index + 1}. {pet.name} ({pet.species})" for index, pet in enumerate(owner.pets)]
    pet_index = st.selectbox(
        "Pet for this task",
        range(len(owner.pets)),
        format_func=lambda index: pet_labels[index],
        key="selected_pet",
    )
    pet = owner.pets[pet_index]
    with st.form("add_task", clear_on_submit=True):
        title = st.text_input("Task title")
        category = st.selectbox("Category", CATEGORIES, format_func=str.capitalize)
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=1440, value=20)
        frequency = st.text_input("Frequency", value="daily")
        due_date = st.date_input("Due date")
        priority = st.selectbox("Priority", PRIORITIES, format_func=str.capitalize)
        if st.form_submit_button("Add task"):
            try:
                pet.add_task(Task(
                    title, int(duration), frequency, priority=priority,
                    category=category, due_date=due_date,
                ))
            except ValueError as exc:
                st.error(str(exc))

    if pet.tasks:
        st.table(
            [
                {
                    "Task": task.description,
                    "Category": task.category.capitalize(),
                    "Minutes": task.duration_minutes,
                    "Frequency": task.frequency,
                    "Due date": task.due_date,
                    "Priority": task.priority.capitalize(),
                    "Completed": task.completed,
                }
                for task in pet.tasks
            ]
        )
        task_labels = [f"{index + 1}. {task.description}" for index, task in enumerate(pet.tasks)]
        selected_index = st.selectbox(
            "Task to edit or remove",
            range(len(pet.tasks)),
            format_func=lambda index: task_labels[index],
            key=f"selected_task_{pet_index}_{st.session_state.edit_version}",
        )
        selected = pet.tasks[selected_index]
        with st.form(f"edit_task_{pet_index}_{selected_index}_{st.session_state.edit_version}"):
            edited_title = st.text_input("Edit task title", value=selected.description)
            edited_category = st.selectbox(
                "Edit category",
                CATEGORIES,
                index=CATEGORIES.index(selected.category),
                format_func=str.capitalize,
            )
            edited_duration = st.number_input(
                "Edit duration (minutes)", min_value=1, max_value=1440, value=selected.duration_minutes
            )
            edited_frequency = st.text_input("Edit frequency", value=selected.frequency)
            edited_due_date = st.date_input("Edit due date", value=selected.due_date)
            edited_priority = st.selectbox(
                "Edit priority",
                PRIORITIES,
                index=PRIORITIES.index(selected.priority),
                format_func=str.capitalize,
            )
            completed = st.checkbox("Completed", value=selected.completed)
            if st.form_submit_button("Save changes"):
                try:
                    updated = Task(
                        edited_title,
                        int(edited_duration),
                        edited_frequency,
                        priority=edited_priority,
                        category=edited_category,
                        due_date=edited_due_date,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    selected.description = updated.description
                    selected.duration_minutes = updated.duration_minutes
                    selected.frequency = updated.frequency
                    selected.priority = updated.priority
                    selected.category = updated.category
                    selected.due_date = updated.due_date
                    if completed:
                        selected.mark_complete()
                    else:
                        selected.mark_incomplete()
                    st.session_state.edit_version += 1
                    st.rerun()
        if st.button("Remove selected task"):
            pet.remove_task(selected)
            st.session_state.edit_version += 1
            st.rerun()
    else:
        st.info("No tasks for this pet yet. Add one above.")
else:
    st.info("Add a pet before adding tasks.")

st.divider()
st.subheader("Daily plan")
st.caption(
    "Suggested times are not medication instructions or fixed appointments. "
    "Follow your veterinarian's advice and any required care times."
)
if st.button("Generate schedule", type="primary"):
    try:
        settings = Owner(owner_name, int(available_minutes), preferred_category)
    except ValueError as exc:
        st.error(str(exc))
    else:
        owner.name = settings.name
        owner.available_minutes = settings.available_minutes
        owner.preferred_category = settings.preferred_category
        if not owner.get_all_tasks():
            st.warning("Add at least one task before generating a schedule.")
        else:
            scheduler = Scheduler(owner)
            plan = scheduler.build_plan(start_time)
            for warning in scheduler.detect_conflicts(plan):
                st.warning(warning)
            scheduled = [item for item in plan if item[2] is not None]
            skipped = [item for item in plan if item[2] is None]
            st.write(f"Plan for {owner.name}'s pets:")
            if scheduled:
                for pet, task, start, end, reason in scheduled:
                    assert start is not None and end is not None
                    end_label = end.strftime("%H:%M")
                    if end.date() != start.date():
                        end_label += " (midnight)"
                    st.markdown(
                        f"**{start:%H:%M}–{end_label} · {pet.name}: {task.description}** "
                        f"({task.category}, {task.duration_minutes} min)"
                    )
                    st.caption(reason)
            elif skipped:
                st.info("No tasks fit in the available time today.")
            else:
                st.info("No incomplete tasks are due today.")
            if skipped:
                st.markdown("**Not scheduled**")
                for pet, task, _, _, reason in skipped:
                    st.write(f"- {pet.name}: {task.description}: {reason}")
