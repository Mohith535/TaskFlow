import json
from pathlib import Path
from task_manager.models import Task

TASKS_FILE = Path("tasks.json")


def load_tasks():
    if not TASKS_FILE.exists():
        return []

    with open(TASKS_FILE, "r") as file:
        data = json.load(file)

    tasks = []
    for item in data:
        tasks.append(Task(**item))

    return tasks


def save_tasks(tasks):
    data = []
    for task in tasks:
        data.append(task.__dict__)

    with open(TASKS_FILE, "w") as file:
        json.dump(data, file, indent=4)
