"""
TaskFlow Commands Module
------------------------
This file contains all CLI task operations.
Designed for clarity, calm UX, and reliability.
"""

from task_manager.storage import load_tasks, save_tasks
from task_manager.models import Task
from datetime import datetime


# =========================================================
# CONFIGURATION
# =========================================================

COL_WIDTHS = {
    "id": 3,
    "status": 6,
    "title": 30,
    "priority": 8,
    "created": 16,
    "completed": 16
}

MAX_VISIBLE_TASKS = 15


# =========================================================
# MESSAGE HELPERS (Emotion-safe output)
# =========================================================

def info(msg):
    print(f"Info: {msg}")

def note(msg):
    print(f"Note: {msg}")

def success(msg):
    print(f"OK: {msg}")

def careful(msg):
    print(f"Careful: {msg}")


def task_not_found(task_id):
    """Unified message when a task ID does not exist."""
    info(f"Task {task_id} isn’t available right now.")


# =========================================================
# UTILITIES
# =========================================================

def normalize_priority(priority):
    """Normalize priority input to Low / Medium / High."""
    if not priority:
        return "Medium"

    priority = priority.strip().lower()

    if priority in ("high", "h"):
        return "High"
    if priority in ("medium", "m"):
        return "Medium"
    if priority in ("low", "l"):
        return "Low"

    return "Medium"


# =========================================================
# CORE TASK CREATION
# =========================================================

def add_task():
    """Add a new task with automatic timestamp."""
    tasks = load_tasks()

    title = input("Task title: ").strip()
    priority_input = input("Priority (Low/Medium/High): ")
    priority = normalize_priority(priority_input)

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

    success("Task added successfully.")


# =========================================================
# LISTING & VIEWING
# =========================================================

def list_tasks(filter_status=None):
    """List tasks with optional filtering and soft output limit."""
    tasks = load_tasks()

    if not tasks:
        note("Your task list is empty. A good place to start.")
        return

    filtered_tasks = []
    for task in tasks:
        if filter_status == "todo" and task.completed:
            continue
        if filter_status == "done" and not task.completed:
            continue
        filtered_tasks.append(task)

    if not filtered_tasks:
        if filter_status == "done":
            note("You haven’t completed any tasks yet.")
        elif filter_status == "todo":
            note("No pending tasks. Everything is completed.")
        else:
            note("No tasks to display right now.")
        return

    # Table header
    print(
        f"{'ID':<{COL_WIDTHS['id']}} | "
        f"{'STATUS':<{COL_WIDTHS['status']}} | "
        f"{'TITLE':<{COL_WIDTHS['title']}} | "
        f"{'PRIORITY':<{COL_WIDTHS['priority']}} | "
        f"{'CREATED':<{COL_WIDTHS['created']}} | "
        f"{'COMPLETED':<{COL_WIDTHS['completed']}}"
    )

    print("-" * (
        COL_WIDTHS['id'] +
        COL_WIDTHS['status'] +
        COL_WIDTHS['title'] +
        COL_WIDTHS['priority'] +
        COL_WIDTHS['created'] +
        COL_WIDTHS['completed'] +
        15
    ))

    shown = 0
    for task in filtered_tasks:
        if shown >= MAX_VISIBLE_TASKS:
            note(f"Showing first {MAX_VISIBLE_TASKS} tasks. Use '--all' to view everything.")
            break

        status = "DONE" if task.completed else "TODO"
        created = task.created_at or "-"
        completed = task.completed_at or "-"

        print(
            f"{task.id:<{COL_WIDTHS['id']}} | "
            f"{status:<{COL_WIDTHS['status']}} | "
            f"{task.title:<{COL_WIDTHS['title']}} | "
            f"{task.priority:<{COL_WIDTHS['priority']}} | "
            f"{created:<{COL_WIDTHS['created']}} | "
            f"{completed:<{COL_WIDTHS['completed']}}"
        )
        shown += 1


def view_task(task_id):
    """View a single task in detail."""
    tasks = load_tasks()

    for task in tasks:
        if task.id == task_id:
            print(f"ID        : {task.id}")
            print(f"Title     : {task.title}")
            print(f"Status    : {'DONE' if task.completed else 'TODO'}")
            print(f"Priority  : {task.priority}")
            print(f"Created   : {task.created_at or '-'}")
            print(f"Completed : {task.completed_at or '-'}")
            return

    task_not_found(task_id)


# =========================================================
# TASK STATE CHANGES
# =========================================================

def complete_task(task_id):
    tasks = load_tasks()

    for task in tasks:
        if task.id == task_id:
            task.completed = True
            task.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_tasks(tasks)
            success(f"Task {task_id} marked as completed.")
            return

    task_not_found(task_id)


def undo_task(task_id):
    tasks = load_tasks()

    for task in tasks:
        if task.id == task_id:
            if not task.completed:
                info(f"Task {task_id} is already TODO.")
                return

            task.completed = False
            task.completed_at = None
            save_tasks(tasks)
            success(f"Task {task_id} moved back to TODO.")
            return

    task_not_found(task_id)


def edit_task(task_id):
    tasks = load_tasks()

    for task in tasks:
        if task.id == task_id:
            new_title = input("New title (leave empty to keep): ").strip()
            new_priority = input("New priority (Low/Medium/High, leave empty to keep): ").strip()

            if new_title:
                task.title = new_title
            if new_priority:
                task.priority = normalize_priority(new_priority)

            save_tasks(tasks)
            success(f"Task {task_id} updated successfully.")
            return

    task_not_found(task_id)


def rename_task(task_id):
    tasks = load_tasks()

    for task in tasks:
        if task.id == task_id:
            new_title = input("New title: ").strip()
            if not new_title:
                note("Title cannot be empty.")
                return

            task.title = new_title
            save_tasks(tasks)
            success("Task renamed successfully.")
            return

    task_not_found(task_id)


def change_priority(task_id, level):
    tasks = load_tasks()
    priority = normalize_priority(level)

    for task in tasks:
        if task.id == task_id:
            task.priority = priority
            save_tasks(tasks)
            success(f"Priority updated to {priority}.")
            return

    task_not_found(task_id)


# =========================================================
# DESTRUCTIVE ACTIONS
# =========================================================

def delete_task(task_id):
    tasks = load_tasks()

    for task in tasks:
        if task.id == task_id:
            tasks.remove(task)
            save_tasks(tasks)
            success(f"Task {task_id} removed successfully.")
            return

    task_not_found(task_id)


def clear_completed_tasks():
    tasks = load_tasks()
    completed = [t for t in tasks if t.completed]

    if not completed:
        note("No completed tasks to clear.")
        return

    confirm = input(
        f"This will permanently delete {len(completed)} completed task(s). Continue? (y/n): "
    ).strip().lower()

    if confirm != "y":
        info("Operation cancelled.")
        return

    tasks = [t for t in tasks if not t.completed]
    save_tasks(tasks)
    success(f"Cleared {len(completed)} completed task(s).")


def reset_tasks():
    tasks = load_tasks()

    if not tasks:
        note("No tasks to reset.")
        return

    confirm = input(
        "This will delete ALL tasks permanently.\nType RESET to confirm: "
    ).strip()

    if confirm != "RESET":
        info("Reset cancelled.")
        return

    save_tasks([])
    success("All tasks have been cleared.")


# =========================================================
# SUMMARY & STATS
# =========================================================

def summary():
    tasks = load_tasks()

    total = len(tasks)
    completed = sum(1 for t in tasks if t.completed)
    pending = total - completed
    high_pending = sum(
        1 for t in tasks if not t.completed and t.priority == "High"
    )

    print(f"You have {total} task(s).")
    print(f"Completed: {completed}")
    print(f"Pending: {pending}")
    print(f"High priority pending: {high_pending}")


def stats_tasks():
    tasks = load_tasks()

    total = len(tasks)
    completed = sum(1 for t in tasks if t.completed)
    pending = total - completed

    print(f"Total     : {total}")
    print(f"Completed : {completed}")
    print(f"Pending   : {pending}")


# =========================================================
# HELP
# =========================================================

def show_help():
    print("TaskFlow — Commands\n")
    print("add                     Add a new task")
    print("list                    List all tasks")
    print("list --todo             List pending tasks")
    print("list --done             List completed tasks")
    print("view <id>               View task details")
    print("complete <id>           Mark a task as completed")
    print("undo <id>               Move task back to TODO")
    print("rename <id>             Rename a task")
    print("priority <id> <level>   Change priority")
    print("delete <id>             Delete a task")
    print("clear completed         Clear all completed tasks")
    print("summary                 Human-readable summary")
    print("stats                   Task statistics")
    print("reset                   Reset all tasks")
    print("help                    Show this help")
