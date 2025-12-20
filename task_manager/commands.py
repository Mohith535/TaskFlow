from task_manager.storage import load_tasks, save_tasks
from task_manager.models import Task
from datetime import datetime

COL_WIDTHS = {
    "id": 3,
    "status": 6,
    "title": 30,
    "priority": 8,
    "created": 16,
    "completed": 16
}



def normalize_priority(priority):
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



def add_task():
    tasks = load_tasks()

    title = input("Task title: ")
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

    print(" Task added successfully!")


def list_tasks(filter_status=None):
    tasks = load_tasks()

    if not tasks:
        print("No tasks found.")
        return

    # Apply filter first
    filtered_tasks = []
    for task in tasks:
        if filter_status == "todo" and task.completed:
            continue
        if filter_status == "done" and not task.completed:
            continue
        filtered_tasks.append(task)

    # Handle empty filtered result
    if not filtered_tasks:
        if filter_status == "done":
            print("You haven’t completed any tasks yet.")
        elif filter_status == "todo":
            print("No pending tasks. Everything is completed.")
        else:
            print("No tasks to display.")
        return

    # Header
    print(
        f"{'ID':<{COL_WIDTHS['id']}} | "
        f"{'STATUS':<{COL_WIDTHS['status']}} | "
        f"{'TITLE':<{COL_WIDTHS['title']}} | "
        f"{'PRIORITY':<{COL_WIDTHS['priority']}} | "
        f"{'CREATED':<{COL_WIDTHS['created']}} | "
        f"{'COMPLETED':<{COL_WIDTHS['completed']}}"
    )

    print("-" * 90)

    for task in filtered_tasks:
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

    print(f"Error: Task with ID {task_id} not found.")


def complete_task(task_id):
    tasks = load_tasks()

    for task in tasks:
        if task.id == task_id:
            task.completed = True
            task.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_tasks(tasks)
            print(f" Task {task_id} marked as completed!")
            return

    print(f"Error: Task with ID {task_id} not found.")

def delete_task(task_id):
    tasks = load_tasks()

    for task in tasks:
        if task.id == task_id:
            tasks.remove(task)
            save_tasks(tasks)
            print(f" Task {task_id} deleted!")
            return

    print(f"Error: Task with ID {task_id} not found.")


def search_tasks(keyword):
    tasks = load_tasks()
    keyword = keyword.lower()

    found = False
    for task in tasks:
        if keyword in task.title.lower():
            status = "DONE" if task.completed else "TODO"
            print(f"{task.id} | {status} | {task.title} | {task.priority}")
            found = True

    if not found:
        print("No matching tasks found.")


def clear_completed_tasks():
    tasks = load_tasks()
    pending_tasks = [task for task in tasks if not task.completed]

    removed_count = len(tasks) - len(pending_tasks)

    if removed_count == 0:
        print("No completed tasks to clear.")
        return

    save_tasks(pending_tasks)
    print(f"Cleared {removed_count} completed task(s).")



def summary():
    tasks = load_tasks()

    total = len(tasks)
    completed = sum(1 for t in tasks if t.completed)
    pending = total - completed
    high_pending = sum(
        1 for t in tasks if not t.completed and t.priority.lower() == "high"
    )

    print(f"You have {total} task(s).")
    print(f"Completed: {completed}")
    print(f"Pending: {pending}")
    print(f"High priority pending: {high_pending}")



def reset_tasks():
    confirm = input("This will delete ALL tasks. Continue? (y/n): ").strip().lower()

    if confirm != "y":
        print("Reset cancelled.")
        return

    save_tasks([])
    print("All tasks have been deleted.")





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

