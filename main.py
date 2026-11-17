"""Run a small multi-pet scheduling example in the terminal."""

from datetime import time

from pawpal_system import Owner, Pet, Scheduler, Task


def main() -> None:
    owner = Owner("Jordan", available_minutes=60, preferred_category="walk")
    dog = Pet("Mochi", "dog")
    cat = Pet("Luna", "cat")

    dog.add_task(Task("Morning walk", 25, "daily", priority="high", category="walk"))
    dog.add_task(Task("Breakfast", 10, "daily", priority="high", category="feeding"))
    cat.add_task(Task("Playtime", 15, "daily", category="enrichment"))
    owner.add_pet(dog)
    owner.add_pet(cat)

    print("Today's Schedule")
    for pet, task, start, end, reason in Scheduler(owner).build_plan(time(9)):
        if start is None or end is None:
            print(f"Not scheduled: {pet.name} - {task.description}. {reason}")
        else:
            print(
                f"{start:%H:%M}-{end:%H:%M} | {pet.name}: "
                f"{task.description} ({task.duration_minutes} min)"
            )
            print(f"  {reason}")


if __name__ == "__main__":
    main()
