#!/usr/bin/env python3
"""
TaskFlow CLI v2.0
-----------------
Calm, Powerful CLI Task Assistant
"""

import sys
from typing import Optional

from task_manager.commands import (
    add_task,
    list_tasks,
    complete_task,
    delete_task,
    rename_task,
    edit_task,
    view_task,
    search_tasks,
    clear_completed_tasks,
    reset_tasks,
    summary,
    stats_tasks,
    show_help,
    undo_task,
    change_priority,
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


def parse_args(args: list) -> dict:
    """Parse command line arguments."""
    parsed = {
        'command': None,
        'id': None,
        'keyword': None,
        'priority': None,
        'tags': [],
        'minutes': 25,
        'date': None,
        'filters': {
            'status': None,
            'priority': None,
            'tag': None,
            'show_all': False
        }
    }
    
    if not args:
        return parsed
    
    parsed['command'] = args[0]
    
    i = 1
    while i < len(args):
        arg = args[i]
        
        if arg.startswith('--'):
            # Handle flags
            if arg == '--all':
                parsed['filters']['show_all'] = True
            elif arg == '--todo':
                parsed['filters']['status'] = 'todo'
            elif arg == '--done':
                parsed['filters']['status'] = 'done'
            elif arg == '--priority' and i + 1 < len(args):
                parsed['filters']['priority'] = args[i + 1]
                i += 1
            elif arg == '--tag' and i + 1 < len(args):
                parsed['filters']['tag'] = args[i + 1]
                i += 1
        elif parsed['id'] is None and arg.isdigit():
            parsed['id'] = int(arg)
        elif parsed['command'] == 'search' and parsed['keyword'] is None:
            parsed['keyword'] = arg
        elif parsed['command'] == 'priority' and parsed['priority'] is None:
            parsed['priority'] = arg
        elif parsed['command'] == 'tag' and arg != parsed['command']:
            parsed['tags'].append(arg)
        elif parsed['command'] == 'focus' and parsed['id'] is not None and arg.isdigit():
            parsed['minutes'] = int(arg)
        elif parsed['command'] == 'schedule' and parsed['date'] is None:
            parsed['date'] = arg
        
        i += 1
    
    return parsed


def handle_search(keyword: str):
    """Handle search command."""
    from task_manager.commands import search_tasks
    if keyword:
        search_tasks(keyword)
    else:
        print("Usage: taskflow search <keyword>")


def handle_focus(args: dict):
    """Handle focus-related commands."""
    if args['id'] is not None:
        focus_task(args['id'], args['minutes'])
    elif args['keyword'] == 'status':
        check_focus()
    elif args['keyword'] == 'end':
        end_focus()
    else:
        print("Usage: taskflow focus <id> [minutes]")
        print("       taskflow focus status")
        print("       taskflow focus end")


def main():
    """Main command router."""
    if len(sys.argv) < 2:
        show_help()
        return
    
    args = parse_args(sys.argv[1:])
    command = args['command']
    
    if command == "add":
        add_task()
    
    elif command == "list":
        list_tasks(
            filter_status=args['filters']['status'],
            filter_priority=args['filters']['priority'],
            filter_tag=args['filters']['tag'],
            show_all=args['filters']['show_all']
        )
    
    elif command == "view":
        if args['id'] is not None:
            view_task(args['id'])
        else:
            print("Usage: taskflow view <id>")
    
    elif command == "edit":
        if args['id'] is not None:
            edit_task(args['id'])
        else:
            print("Usage: taskflow edit <id>")
    
    elif command == "rename":
        if args['id'] is not None:
            rename_task(args['id'])
        else:
            print("Usage: taskflow rename <id>")
    
    elif command == "complete":
        if args['id'] is not None:
            complete_task(args['id'])
        else:
            print("Usage: taskflow complete <id>")
    
    elif command == "undo":
        if args['id'] is not None:
            undo_task(args['id'])
        else:
            print("Usage: taskflow undo <id>")
    
    elif command == "priority":
        if args['id'] is not None and args['priority']:
            change_priority(args['id'], args['priority'])
        else:
            print("Usage: taskflow priority <id> <L|M|H>")
    
    elif command == "delete":
        if args['id'] is not None:
            delete_task(args['id'])
        else:
            print("Usage: taskflow delete <id>")
    
    elif command == "search":
        if args['keyword']:
            handle_search(args['keyword'])
        else:
            print("Usage: taskflow search <keyword>")
    
    elif command == "focus":
        handle_focus(args)
    
    elif command == "schedule":
        if args['id'] is not None and args['date']:
            schedule_task(args['id'], args['date'])
        else:
            print("Usage: taskflow schedule <id> <date>")
            print("       date format: YYYY-MM-DD, 'today', or 'tomorrow'")
    
    elif command == "today":
        show_today_tasks()
    
    elif command == "note":
        if args['id'] is not None:
            add_note(args['id'])
        else:
            print("Usage: taskflow note <id>")
    
    elif command == "tag":
        if args['id'] is not None and args['tags']:
            tag_task(args['id'], args['tags'])
        else:
            print("Usage: taskflow tag <id> <tag1> [tag2...]")
    
    elif command == "clear" and len(sys.argv) > 2 and sys.argv[2] == "completed":
        clear_completed_tasks()
    
    elif command == "backup":
        backup_tasks()
    
    elif command == "reset":
        reset_tasks()
    
    elif command == "summary":
        summary()
    
    elif command == "stats":
        stats_tasks()
    
    elif command == "help":
        show_help()
    
    elif command == "version":
        show_version()
    
    else:
        print(f"Unknown command: {command}")
        print("Type 'taskflow help' for available commands")


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