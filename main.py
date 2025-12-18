import sys
from task_manager.commands import (
    add_task,
    list_tasks,
    complete_task,
    delete_task,
    stats_tasks,
    show_help,
)



def main():
    if len(sys.argv) < 2:
        show_help()
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

    elif command == "help":
        show_help()

    else:
        print("Unknown command")


if __name__ == "__main__":
    main()
