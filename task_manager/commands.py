from task_manager.storage import load_tasks, save_tasks
from task_manager.models import Task
from datetime import datetime


def add_task():
    tasks = load_tasks()

    title = input("Task title: ")
    priority = input("Priority (Low/Medium/High): ")

    task_id = len(tasks) + 1
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    task = Task(
        id=task_id,
        title=title,
        priority=priority,
        created_at=now
    )


    tasks.append(task)
    save_tasks(tasks)

    print(" Task added successfully!")


def list_tasks():
    tasks = load_tasks()

    if not tasks:
        print("No tasks found.")
        return

    print(
        f"{'ID':<2} | {'STATUS':<6} | {'TITLE':<27} | {'PRIORITY':<8} | "
        f"{'CREATED':<16} | {'COMPLETED':<16}"
        )
    
    print("-" * 90)

    for task in tasks:
        status = "DONE" if task.completed else "TODO"
        created = task.created_at if task.created_at else "-"
        completed = task.completed_at if task.completed_at else "-"

        print(
            f"{task.id:<2} | {status:<6} | {task.title:<27} | {task.priority:<8} | "
            f"{created:<16} | {completed:<16}"
        )

def list_tasks(filter_status=None):
    tasks = load_tasks()

    if not tasks:
        print("No tasks found.")
        return

    print("ID | STATUS | TITLE                     | PRIORITY | CREATED             | COMPLETED")
    print("-" * 80)

    for task in tasks:
        if filter_status == "todo" and task.completed:
            continue
        if filter_status == "done" and not task.completed:
            continue

        status = "DONE" if task.completed else "TODO"

        print(
            f"{task.id:<3}| "
            f"{status:<6}| "
            f"{task.title:<25}| "
            f"{task.priority:<8}| "
            f"{(task.created_at or '-'): <19}| "
            f"{(task.completed_at or '-'): <19}"
        )


def undo_task(task_id):
    tasks = load_tasks()

    for task in tasks:
        if task.id == task_id:
            if not task.completed:
                print(f"Task {task_id} is already TODO.")
                return

            task.completed = False
            task.completed_at = None
            save_tasks(tasks)

            print(f"Task {task_id} marked as TODO again.")
            return

    print("Task not found.")


def edit_task(task_id):
    tasks = load_tasks()

    for task in tasks:
        if task.id == task_id:
            print(f"Current title: {task.title}")
            new_title = input("New title (leave empty to keep): ").strip()

            print(f"Current priority: {task.priority}")
            new_priority = input("New priority (Low/Medium/High, leave empty to keep): ").strip()

            if new_title:
                task.title = new_title

            if new_priority:
                task.priority = new_priority

            save_tasks(tasks)
            print(f"Task {task_id} updated successfully.")
            return

    print("Task not found.")


def complete_task(task_id):
    tasks = load_tasks()

    for task in tasks:
        if task.id == task_id:
            task.completed = True
            task.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
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

def stats_tasks():
    tasks = load_tasks()

    total = len(tasks)
    completed = sum(1 for task in tasks if task.completed)
    pending = total - completed

    print(f"Total tasks   : {total}")
    print(f"Completed     : {completed}")
    print(f"Pending       : {pending}")

def show_help():
    print("CLI Task Manager – Commands\n")
    print("add                 Add a new task")
    print("list                List all tasks")
    print("complete <id>       Mark a task as completed")
    print("delete <id>         Delete a task")
    print("stats               Show task statistics")
    print("help                Show this help message")

