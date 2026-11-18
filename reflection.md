# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

The UML has four classes:

- **Owner** holds the owner's name, available time, and preferred task category.
- **Pet** holds the pet's name and species and references its owner.
- **CareTask** describes a task using its title, category, duration, and priority.
- **DailyPlanner** brings a pet and a list of tasks together. Its `build_plan`
  method is intended to choose and order tasks within the owner's constraints
  and explain the result.

The planner handles one pet at a time; multiple pets can reference the same
owner. Tasks are associated with a pet through the planner rather than directly.

Reviewing the skeleton revealed a few limitations:

- A task has no direct pet reference or completion status. The planner assumes
  the supplied tasks are for its pet, so a future multi-pet or completion-tracking
  feature would need a more explicit relationship.
- The skeleton has no due times or recurring schedules. A priority-and-time
  budget alone cannot guarantee that medication or other time-sensitive care
  happens at the required time.
- `build_plan` is still a stub in `pawpal_system.py`; the separate working
  implementation is in `pawpal.py`. Keeping both long term could cause them to
  diverge, so they should be consolidated when the skeleton is implemented.
- The existing implementation uses a greedy priority-first selection. A long
  high-priority task can leave unused time or prevent several shorter tasks
  from fitting; sorting is unlikely to be a performance bottleneck for a
  typical daily task list.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

Yes. The planner originally referenced the owner and pet separately. The design
was changed so the pet references its owner and the planner accesses the owner
through the pet. This makes the relationship explicit and prevents the planner
from being given an owner who differs from the pet's owner. No further class
changes were made during this review; the limitations above are noted for
future work rather than adding complexity to the draft.

Later, the core implementation in `pawpal_system.py` changed to `Task`, `Pet`,
`Owner`, and `Scheduler` to support multiple pets. An owner now holds pets,
each pet holds its tasks, and the scheduler retrieves all pet-task pairs through
`Owner.get_all_tasks()`. Tasks have a completion status and frequency. Daily
and weekly tasks now create a new occurrence when completed, due one or seven
days after completion. The Streamlit app uses the multi-pet backend: users add
pets and their tasks, then generate a shared schedule.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

The scheduler considers available minutes, the time remaining before midnight,
task duration, priority, preferred category, completion status, and due date.
I put priority first so important care comes before preferences; the preferred
category breaks ties between tasks of the same priority. Only incomplete tasks
due today or earlier are considered.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

The scheduler greedily chooses tasks in priority order rather than searching
every possible combination. A long high-priority task can use time that might
otherwise fit several shorter tasks, so the plan may not maximize the number
of tasks completed. This is reasonable for a busy owner because it keeps the
plan simple and predictable while giving important care priority.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

I used AI to draft the four-class UML, build the initial single-pet planner,
and develop the multi-pet backend, terminal example, and tests. The AI
suggested a priority-first scheduler that uses the owner's preferred category
to break ties and explains tasks that do not fit. Specific prompts about class
relationships, gathering tasks across pets, and testing completion and task
addition helped turn the design into concrete behavior.

The most effective features were design brainstorming, iterative code
generation, and debugging with test feedback. For example, the assistant helped
translate the UML into the four backend classes, then used focused tests and
the terminal demo to check sorting, recurrence, and conflict warnings. It also
connected scheduler results to the Streamlit interface. Reviewing the output
and directing each change kept me responsible for the design decisions.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

I chose duration in minutes as the meaning of task time and initially chose a
descriptive frequency label instead of automatic recurrence. I also directed the design
toward multiple pets: the scheduler now gathers tasks through
`Owner.get_all_tasks()` rather than planning for just one pet.

For conflict detection, I chose to check supplied scheduled intervals rather
than add fixed start times to every task. This modified the more complex design
option and kept task input focused on duration. The tradeoff is that generated
plans are consecutive and cannot represent fixed appointments.

We ran the terminal example and checked that it showed three tasks for two
pets. We also ran pytest tests for multi-pet scheduling, task completion, and
task addition. When the full suite exposed a test-module name collision, the
AI added `tests/__init__.py`; rerunning the suite collected and passed all 33
tests. Those results preceded the multi-pet UI integration; the updated UI
tests also exercise adding pets, editing tasks, and scheduling across pets.

**c. Organizing chat sessions**

Using separate chats for design, implementation, testing, and UI integration
can keep each conversation focused and make it easier to find decisions and
results for a phase. A fresh chat does not automatically contain every earlier
decision, so I would carry forward the relevant UML, requirements, and test
results and ask the assistant to inspect the current files before making
changes. That keeps the work organized without treating old suggestions as
authoritative over the final implementation.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

I tested multi-pet scheduling, task addition and completion, duration sorting,
filtering, daily recurrence, conflict warnings, and Streamlit interactions.
These checks help ensure care is assigned to the right pet, plans respect the
available time, and important edge cases do not go unnoticed.

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

My confidence is **4 out of 5**: a recorded full test run passed 48 tests, but
tests cannot cover every real-world situation. I would add broader tests for
long sequences of editing, completing, and reopening recurring tasks, including
month and year boundaries.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

I am most satisfied with bringing tasks from multiple pets into one
priority-based plan that explains its choices.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

I would add persistent storage and explore fixed-time appointments so the
planner can better support care that must happen at a specific time.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

As the lead architect, I set the requirements and make the final design
decisions. AI can suggest and implement ideas, but I need to assess the
tradeoffs and verify the results against the project's goals.
