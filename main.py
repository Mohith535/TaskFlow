import sys
from task_manager.commands import add_task, list_tasks


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py [add | list]")
        return

    command = sys.argv[1]

    if command == "add":
        add_task()
    elif command == "list":
        list_tasks()
    else:
        print("Unknown command")


if __name__ == "__main__":
    main()
