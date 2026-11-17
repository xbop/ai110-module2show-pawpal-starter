from streamlit.testing.v1 import AppTest


def test_add_edit_schedule_and_remove_task():
    app = AppTest.from_file("app.py", default_timeout=30).run()
    assert not app.exception

    app.text_input[3].input("Morning walk")
    app.button[0].click().run()
    assert len(app.session_state.tasks) == 1
    assert app.session_state.tasks[0].title == "Morning walk"

    app.text_input[4].input("Evening walk")
    app.number_input[2].set_value(35)
    app.button[1].click().run()
    assert app.session_state.tasks[0].title == "Evening walk"
    assert app.session_state.tasks[0].duration_minutes == 35

    app.button[-1].click().run()
    assert any("Evening walk" in element.value for element in app.markdown)
    assert not app.exception

    app.button[2].click().run()
    assert len(app.session_state.tasks) == 0
    assert not app.exception


def test_empty_task_and_missing_name_show_errors():
    app = AppTest.from_file("app.py", default_timeout=30).run()
    app.button[0].click().run()
    assert any("Task title cannot be empty" in element.value for element in app.error)
    app.text_input[0].input(" ")
    app.button[-1].click().run()
    assert any("Owner name cannot be empty" in element.value for element in app.error)


def test_preference_and_skipped_tasks_are_shown():
    app = AppTest.from_file("app.py", default_timeout=30).run()
    app.text_input[3].input("Feed")
    app.selectbox[1].select("feeding")
    app.number_input[1].set_value(20)
    app.button[0].click().run()

    app.text_input[3].input("Walk")
    app.selectbox[1].select("walk")
    app.number_input[1].set_value(20)
    app.button[0].click().run()

    app.number_input[0].set_value(20)
    app.selectbox[0].select("walk")
    app.button[-1].click().run()
    assert any("Walk" in element.value for element in app.markdown)
    assert any("matches your preferred category" in element.value for element in app.caption)
    assert any("Feed" in element.value for element in app.markdown)
    assert not app.exception

    app.selectbox[3].select(1).run()
    assert app.text_input[4].value == "Walk"
    app.button[2].click().run()
    assert [task.title for task in app.session_state.tasks] == ["Feed"]
    assert not app.exception
