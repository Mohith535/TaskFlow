import sys
from task_manager.commands import (
    add_task,
    change_priority,
    list_tasks,
    complete_task,
    delete_task,
    rename_task,
    stats_tasks,
    show_help,
    undo_task,
    edit_task,
    search_tasks,
    clear_completed_tasks,
    summary,
    reset_tasks,
    view_task,
)

APP_NAME = "TaskFlow"
APP_VERSION = "v1.1"
APP_TAGLINE = "Power Commands Update"


def show_version():
    print(f"{APP_NAME} {APP_VERSION} — {APP_TAGLINE}")


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

    elif command == "search":
        if len(sys.argv) < 3:
            print("Usage: python main.py search <keyword>")
        else:
            search_tasks(sys.argv[2])

    elif command == "clear" and len(sys.argv) > 2 and sys.argv[2] == "completed":
        clear_completed_tasks()

    elif command == "summary":
        summary()

    elif command == "reset":
        reset_tasks()


    elif command == "stats":
        stats_tasks()

    elif command == "help":
        show_help()

    elif command == "view":
        if len(sys.argv) < 3:
            print("Usage: python main.py view <id>")
        else:
            view_task(int(sys.argv[2]))

    elif command == "rename":
        if len(sys.argv) < 3:
            print("Usage: python main.py rename <id>")
        else:
            rename_task(int(sys.argv[2]))

    elif command == "priority":
        if len(sys.argv) < 4:
            print("Usage: python main.py priority <id> <low|medium|high>")
        else:
            change_priority(int(sys.argv[2]), sys.argv[3])

    elif command == "version":
        show_version()

    else:
        print("Unknown command")


if __name__ == "__main__":
    main()
