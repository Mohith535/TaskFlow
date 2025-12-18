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
        status = "[DONE]" if task.completed else "[TODO]"
        print(f"{status} {task.id}. {task.title} ({task.priority})")

def complete_task(task_id):
    tasks = load_tasks()

    for task in tasks:
        if task.id == task_id:
            task.completed = True
            save_tasks(tasks)
            print(f" Task {task_id} marked as completed!")
            return

    print("Task not found.")

def delete_task(task_id):
    tasks = load_tasks()

    for task in tasks:
        if task.id == task_id:
            tasks.remove(task)
            save_tasks(tasks)
            print(f" Task {task_id} deleted!")
            return

    print("Task not found.")


