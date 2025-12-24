#!/usr/bin/env python3
"""
TaskFlow CLI v2.0
-----------------
Calm, Powerful CLI Task Assistant
"""

import sys
import os

# Fix for Windows console encoding
if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    os.system('chcp 65001 > nul')  # Set console to UTF-8

from typing import Optional

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
    # v2.0 time management commands
    focus_task,
    check_focus,
    end_focus,
    schedule_task,
    show_today_tasks,
    add_note,
    tag_task,
    backup_tasks
)

APP_NAME = "TaskFlow"
APP_VERSION = "v2.0"
APP_TAGLINE = "Calm, Powerful CLI Task Assistant"


def show_version():
    """Show version information."""
    print(f"{APP_NAME} {APP_VERSION} — {APP_TAGLINE}")
    print("Time Management & Focus Features Enabled")


def safe_int(value: str) -> Optional[int]:
    """Safely convert string to integer."""
    try:
        return int(value)
    except ValueError:
        return None


def main():
    """Main command router."""
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1]

    # --- SPECIAL HANDLING for focus subcommands ---
    if command == "focus":
        if len(sys.argv) == 3:
            sub_cmd = sys.argv[2]
            if sub_cmd == "status":
                check_focus()
                return
            elif sub_cmd == "end":
                end_focus()
                return
        # If we get here, it's either "focus <id>" or invalid
        # Continue to main routing below

    # --- MAIN COMMAND ROUTING ---
    if command == "add":
        # Ignore any flags/arguments for now, just call add_task()
        # This prevents "--invalid" from breaking the command
        add_task()

    elif command == "list":
        args = sys.argv[2:]  # all flags after 'list'
        show_all = "--all" in args

        if "--todo" in args:
            list_tasks(filter_status="todo", show_all=show_all)
        elif "--done" in args:
            list_tasks(filter_status="done", show_all=show_all)
        else:
            list_tasks(show_all=show_all)

    elif command == "undo":
        if len(sys.argv) != 3:
            print("Usage: python main.py undo <id>")
        else:
            task_id = safe_int(sys.argv[2])
            if task_id is None:
                print("Info: Please provide a valid numeric task ID.")
            else:
                undo_task(task_id)

    elif command == "edit":
        if len(sys.argv) != 3:
            print("Usage: python main.py edit <id>")
        else:
            task_id = safe_int(sys.argv[2])
            if task_id is None:
                print("Info: Please provide a valid numeric task ID.")
            else:
                edit_task(task_id)

    elif command == "complete":
        if len(sys.argv) < 3:
            print("Please provide task ID.")
            return
        
        task_id = safe_int(sys.argv[2])
        if task_id is None:
            print("Info: Please provide a valid numeric task ID.")
        else:
            complete_task(task_id)

    elif command == "delete":
        if len(sys.argv) < 3:
            print("Please provide task ID.")
            return
        
        task_id = safe_int(sys.argv[2])
        if task_id is None:
            print("Info: Please provide a valid numeric task ID.")
        else:
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
            task_id = safe_int(sys.argv[2])
            if task_id is None:
                print("Info: Please provide a valid numeric task ID.")
            else:
                view_task(task_id)

    elif command == "rename":
        if len(sys.argv) < 3:
            print("Usage: python main.py rename <id>")
        else:
            task_id = safe_int(sys.argv[2])
            if task_id is None:
                print("Info: Please provide a valid numeric task ID.")
            else:
                rename_task(task_id)

    elif command == "priority":
        if len(sys.argv) < 4:
            print("Usage: python main.py priority <id> <low|medium|high>")
        else:
            task_id = safe_int(sys.argv[2])
            if task_id is None:
                print("Info: Please provide a valid numeric task ID.")
            else:
                change_priority(task_id, sys.argv[3])

    elif command == "focus":
        # Handle "focus <id> [minutes]" - already handled "status" and "end" above
        if len(sys.argv) < 3:
            print("Usage: python main.py focus <id> [minutes]")
            print("       python main.py focus status")
            print("       python main.py focus end")
            return
        
        task_id = safe_int(sys.argv[2])
        if task_id is None:
            print(f"Info: Invalid focus command. Use 'focus <id> [minutes]', 'focus status', or 'focus end'")
            return
        
        minutes = 25  # default
        if len(sys.argv) >= 4:
            minutes_arg = safe_int(sys.argv[3])
            minutes = minutes_arg if minutes_arg is not None else 25
        
        focus_task(task_id, minutes)

    elif command == "schedule":
        if len(sys.argv) < 4:
            print("Usage: python main.py schedule <id> <date>")
            print("       date format: YYYY-MM-DD, 'today', or 'tomorrow'")
        else:
            task_id = safe_int(sys.argv[2])
            if task_id is None:
                print("Info: Please provide a valid numeric task ID.")
            else:
                schedule_task(task_id, sys.argv[3])

    elif command == "today":
        show_today_tasks()

    elif command == "note":
        if len(sys.argv) < 3:
            print("Usage: python main.py note <id>")
        else:
            task_id = safe_int(sys.argv[2])
            if task_id is None:
                print("Info: Please provide a valid numeric task ID.")
            else:
                add_note(task_id)

    elif command == "tag":
        if len(sys.argv) < 4:
            print("Usage: python main.py tag <id> <tag1> [tag2...]")
        else:
            task_id = safe_int(sys.argv[2])
            if task_id is None:
                print("Info: Please provide a valid numeric task ID.")
            else:
                tags = sys.argv[3:]
                tag_task(task_id, tags)

    elif command == "backup":
        backup_tasks()

    elif command == "version":
        show_version()

    else:
        print("Info: Unknown command.")
        show_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTaskFlow session ended gracefully.")
        print("Remember: Progress, not perfection. 💫")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        print("Please report this issue if it persists.")
        sys.exit(1)