import sys
from task_manager.commands import (
    add_task,
    list_tasks,
    complete_task,
    delete_task,
    stats_tasks,
)



def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py [add | list | complete | delete | stats]")
        return

    command = sys.argv[1]

    if command == "add":
        add_task()

    elif command == "list":
        list_tasks()

    elif command == "complete":
        if len(sys.argv) < 3:
            print("Please provide task ID.")
            return

        task_id = int(sys.argv[2])
        complete_task(task_id)

    elif command == "delete":
        if len(sys.argv) < 3:
            print("Please provide task ID.")
            return

        task_id = int(sys.argv[2])
        delete_task(task_id)

    elif command == "stats":
        stats_tasks()


    else:
        print("Unknown command")


if __name__ == "__main__":
    main()
