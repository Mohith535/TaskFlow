from task_manager.storage import load_tasks, save_tasks
from task_manager.models import Task


def add_task():
    tasks = load_tasks()

    title = input("Task title: ")
    priority = input("Priority (Low/Medium/High): ")

    task_id = len(tasks) + 1
    task = Task(id=task_id, title=title, priority=priority)

    tasks.append(task)
    save_tasks(tasks)

    print("✅ Task added successfully!")


def list_tasks():
    tasks = load_tasks()

    if not tasks:
        print("No tasks found.")
        return

    for task in tasks:
        status = "✔" if task.completed else "✘"
        print(f"[{status}] {task.id}. {task.title} ({task.priority})")
