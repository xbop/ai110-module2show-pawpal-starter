"""Run a small multi-pet scheduling example in the terminal."""

from datetime import datetime, time, timedelta

from pawpal_system import Owner, Pet, Scheduler, Task


def main() -> None:
    owner = Owner("Jordan", available_minutes=60, preferred_category="walk")
    dog = Pet("Mochi", "dog")
    cat = Pet("Luna", "cat")

    dog.add_task(Task("Morning walk", 25, "daily", priority="high", category="walk"))
    dog.add_task(Task("Breakfast", 10, "daily", priority="high", category="feeding"))
    cat.add_task(Task("Playtime", 15, "daily", category="enrichment"))
    cat.add_task(Task("Grooming", 5, "weekly", completed=True, category="grooming"))
    owner.add_pet(dog)
    owner.add_pet(cat)

    scheduler = Scheduler(owner)
    print("Tasks sorted by duration (including completed tasks)")
    for pet, task in scheduler.sort_by_time():
        print(f"{task.duration_minutes} min | {pet.name}: {task.description}")

    print("\nIncomplete tasks for Luna")
    for pet, task in scheduler.filter_tasks(completed=False, pet_name="Luna"):
        print(f"{pet.name}: {task.description}")

    print("\nCompleted tasks")
    for pet, task in scheduler.filter_tasks(completed=True):
        print(f"{pet.name}: {task.description}")

    print()
    print("Today's Schedule")
    for pet, task, start, end, reason in scheduler.build_plan(time(9)):
        if start is None or end is None:
            print(f"Not scheduled: {pet.name} - {task.description}. {reason}")
        else:
            print(
                f"{start:%H:%M}-{end:%H:%M} | {pet.name}: "
                f"{task.description} ({task.duration_minutes} min)"
            )
            print(f"  {reason}")

    print("\nConflict detection example (manually overlapping times)")
    start = datetime.combine(datetime.today().date(), time(9))
    overlapping_plan = [
        (dog, dog.tasks[0], start, start + timedelta(minutes=25), "Example"),
        (cat, cat.tasks[0], start + timedelta(minutes=10), start + timedelta(minutes=25), "Example"),
    ]
    for warning in scheduler.detect_conflicts(overlapping_plan):
        print(f"Warning: {warning}")


if __name__ == "__main__":
    main()
