from datetime import time

import streamlit as st

from pawpal import CATEGORIES, PRIORITIES, CareTask, DailyPlanner, Owner, Pet


st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.write("Make a practical care plan for your pet, based on the time you have.")

if "tasks" not in st.session_state:
    st.session_state.tasks = []
if "edit_version" not in st.session_state:
    st.session_state.edit_version = 0

st.subheader("Owner and pet")
owner_name = st.text_input("Owner name", value="Jordan")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.text_input("Species", value="dog")
available_minutes = st.number_input(
    "Time available today (minutes)", min_value=0, max_value=1440, value=60
)
start_time = st.time_input("Start time", value=time(9, 0), step=60)
preferred_category = st.selectbox(
    "Preferred task category", ("none", *CATEGORIES), format_func=str.capitalize
)
st.caption("Preference breaks ties between tasks of the same priority.")

st.subheader("Care tasks")
with st.form("add_task", clear_on_submit=True):
    title = st.text_input("Task title")
    category = st.selectbox("Category", CATEGORIES, format_func=str.capitalize)
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=1440, value=20)
    priority = st.selectbox("Priority", PRIORITIES, format_func=str.capitalize)
    if st.form_submit_button("Add task"):
        try:
            st.session_state.tasks.append(
                CareTask(title, category, int(duration), priority)
            )
        except ValueError as exc:
            st.error(str(exc))

if st.session_state.tasks:
    st.table(
        [
            {
                "Task": task.title,
                "Category": task.category.capitalize(),
                "Minutes": task.duration_minutes,
                "Priority": task.priority.capitalize(),
            }
            for task in st.session_state.tasks
        ]
    )
    task_labels = [f"{index + 1}. {task.title}" for index, task in enumerate(st.session_state.tasks)]
    selected_index = st.selectbox(
        "Task to edit or remove",
        range(len(st.session_state.tasks)),
        format_func=lambda index: task_labels[index],
    )
    selected = st.session_state.tasks[selected_index]
    with st.form(f"edit_task_{selected_index}_{st.session_state.edit_version}"):
        edited_title = st.text_input("Edit task title", value=selected.title)
        edited_category = st.selectbox(
            "Edit category",
            CATEGORIES,
            index=CATEGORIES.index(selected.category),
            format_func=str.capitalize,
        )
        edited_duration = st.number_input(
            "Edit duration (minutes)",
            min_value=1,
            max_value=1440,
            value=selected.duration_minutes,
        )
        edited_priority = st.selectbox(
            "Edit priority",
            PRIORITIES,
            index=PRIORITIES.index(selected.priority),
            format_func=str.capitalize,
        )
        if st.form_submit_button("Save changes"):
            try:
                st.session_state.tasks[selected_index] = CareTask(
                    edited_title, edited_category, int(edited_duration), edited_priority
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state.edit_version += 1
                st.rerun()
    if st.button("Remove selected task"):
        st.session_state.tasks.pop(selected_index)
        st.session_state.edit_version += 1
        st.rerun()
else:
    st.info("No tasks yet. Add one above.")

st.divider()
st.subheader("Daily plan")
st.caption(
    "Suggested times are not medication instructions or fixed appointments. "
    "Follow your veterinarian's advice and any required care times."
)
if st.button("Generate schedule", type="primary"):
    try:
        owner = Owner(owner_name, int(available_minutes), preferred_category)
        pet = Pet(pet_name, species, owner)
    except ValueError as exc:
        st.error(str(exc))
    else:
        if not st.session_state.tasks:
            st.warning("Add at least one task before generating a schedule.")
        else:
            plan = DailyPlanner(pet, st.session_state.tasks).build_plan(start_time)
            scheduled = [item for item in plan if item[1] is not None]
            skipped = [item for item in plan if item[1] is None]
            st.write(f"Plan for {pet.name} ({pet.species}), with {owner.name}:")
            if scheduled:
                for task, start, end, reason in scheduled:
                    assert start is not None and end is not None
                    end_label = end.strftime("%H:%M")
                    if end.date() != start.date():
                        end_label += " (midnight)"
                    st.markdown(
                        f"**{start:%H:%M}–{end_label} · {task.title}** "
                        f"({task.category}, {task.duration_minutes} min)"
                    )
                    st.caption(reason)
            else:
                st.info("No tasks fit in the available time today.")
            if skipped:
                st.markdown("**Not scheduled**")
                for task, _, _, reason in skipped:
                    st.write(f"- {task.title}: {reason}")
