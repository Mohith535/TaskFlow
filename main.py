import sys
from task_manager.commands import (
    add_task,
    list_tasks,
    complete_task,
    delete_task,
    stats_tasks,
    show_help,
    undo_task,
    edit_task,
)



def main():
    if len(sys.argv) < 2:
        show_help()
        return


    command = sys.argv[1]

    if command == "add":
        add_task()

    elif command == "list":
        if len(sys.argv) == 3 and sys.argv[2] == "--todo":
            list_tasks(filter_status="todo")
        elif len(sys.argv) == 3 and sys.argv[2] == "--done":
            list_tasks(filter_status="done")
        else:
            list_tasks()


    elif command == "undo":
        if len(sys.argv) != 3:
            print("Usage: python main.py undo <id>")
        else:
            undo_task(int(sys.argv[2]))

    elif command == "edit":
        if len(sys.argv) != 3:
            print("Usage: python main.py edit <id>")
        else:
            edit_task(int(sys.argv[2]))


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
