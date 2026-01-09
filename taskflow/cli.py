#!/usr/bin/env python3
"""
TaskFlow CLI v2.1
-----------------
Calm, Powerful CLI Task Assistant
"""

import sys
import os
import argparse

# Fix for Windows console encoding
if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    os.system('chcp 65001 > nul')  # Set console to UTF-8

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


def create_parser():
    """Create argparse parser that matches your command structure."""
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} {APP_VERSION} — {APP_TAGLINE}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  taskflow add
  taskflow list --todo --priority high
  taskflow focus 6 1
  taskflow schedule 8 today
  taskflow stats
        """,
        add_help=False  # We'll handle help manually
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add command (no arguments - uses interactive input)
    subparsers.add_parser('add', help='Add a new task (interactive)')
    
    # List command with flags
    list_parser = subparsers.add_parser('list', help='List tasks with filtering')
    list_parser.add_argument('--todo', action='store_true', help='Show only pending tasks')
    list_parser.add_argument('--done', action='store_true', help='Show only completed tasks')
    list_parser.add_argument('--priority', choices=['low', 'medium', 'high'], 
                           help='Filter by priority')
    list_parser.add_argument('--tag', help='Filter by tag')
    list_parser.add_argument('--all', action='store_true', 
                           help='Show all tasks (no 10-task limit)')
    
    # Task operations with single ID argument
    id_commands = [
        ('view', 'View task details'),
        ('edit', 'Edit a task'),
        ('rename', 'Rename a task'),
        ('complete', 'Mark task as completed'),
        ('undo', 'Move task back to TODO'),
        ('delete', 'Delete a task'),
        ('note', 'Add/update notes for a task')
    ]
    
    for cmd, help_text in id_commands:
        cmd_parser = subparsers.add_parser(cmd, help=help_text)
        cmd_parser.add_argument('id', type=int, help='Task ID')
    
    # Focus command - YOUR SYNTAX: focus <id> [minutes]
    focus_parser = subparsers.add_parser('focus', help='Focus session commands')
    focus_group = focus_parser.add_mutually_exclusive_group(required=True)
    focus_group.add_argument('--id', type=int, help='Task ID to focus on')
    focus_group.add_argument('--status', action='store_true', help='Check focus status')
    focus_group.add_argument('--end', action='store_true', help='End focus session')
    focus_parser.add_argument('--minutes', type=int, default=25, 
                            help='Focus duration in minutes (default: 25)')
    
    # Priority command
    priority_parser = subparsers.add_parser('priority', help='Change task priority')
    priority_parser.add_argument('id', type=int, help='Task ID')
    priority_parser.add_argument('level', choices=['low', 'medium', 'high'], 
                               help='New priority level')
    
    # Schedule command  
    schedule_parser = subparsers.add_parser('schedule', help='Schedule a task')
    schedule_parser.add_argument('id', type=int, help='Task ID')
    schedule_parser.add_argument('date', help='Date (YYYY-MM-DD, "today", or "tomorrow")')
    
    # Tag command
    tag_parser = subparsers.add_parser('tag', help='Add tags to a task')
    tag_parser.add_argument('id', type=int, help='Task ID')
    tag_parser.add_argument('tags', nargs='+', help='Tags to add')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search tasks by keyword')
    search_parser.add_argument('keyword', help='Search keyword')
    
    # Simple commands without arguments
    simple_commands = [
        ('today', "Show today's scheduled tasks"),
        ('stats', 'Show task statistics'),
        ('summary', 'Human-readable summary'),
        ('backup', 'Create manual backup'),
        ('clear', 'Clear completed tasks'),
        ('reset', 'Reset all tasks (with confirmation)'),
        ('version', 'Show version information'),
        ('help', 'Show help message')
    ]
    
    for cmd, help_text in simple_commands:
        subparsers.add_parser(cmd, help=help_text)
    
    return parser


def main():
    """Main command router using argparse."""
    parser = create_parser()
    
    # Show help if no arguments
    if len(sys.argv) == 1:
        show_help()
        return
    
    # Special case: help command
    if sys.argv[1] in ['help', '--help', '-h']:
        show_help()
        return
    
    try:
        args = parser.parse_args()
    except SystemExit:
        # argparse prints help on error, but we want our help
        show_help()
        return
    
    # If no command specified, show help
    if not hasattr(args, 'command') or args.command is None:
        show_help()
        return
    
    # Route commands
    try:
        if args.command == 'add':
            add_task()
        
        elif args.command == 'list':
            # Determine filter status
            filter_status = None
            if args.todo:
                filter_status = 'todo'
            elif args.done:
                filter_status = 'done'
            
            list_tasks(
                filter_status=filter_status,
                filter_priority=args.priority,
                filter_tag=args.tag,
                show_all=args.all
            )
        
        elif args.command == 'view':
            view_task(args.id)
        
        elif args.command == 'edit':
            edit_task(args.id)
        
        elif args.command == 'rename':
            rename_task(args.id)
        
        elif args.command == 'complete':
            complete_task(args.id)
        
        elif args.command == 'undo':
            undo_task(args.id)
        
        elif args.command == 'delete':
            delete_task(args.id)
        
        elif args.command == 'note':
            add_note(args.id)
        
        elif args.command == 'focus':
            if args.status:
                check_focus()
            elif args.end:
                end_focus()
            elif args.id:
                focus_task(args.id, args.minutes)
            else:
                print("Use: taskflow focus --id 6 [--minutes 25]")
                print("     taskflow focus --status")
                print("     taskflow focus --end")
        
        elif args.command == 'priority':
            change_priority(args.id, args.level)
        
        elif args.command == 'schedule':
            schedule_task(args.id, args.date)
        
        elif args.command == 'today':
            show_today_tasks()
        
        elif args.command == 'tag':
            tag_task(args.id, args.tags)
        
        elif args.command == 'search':
            search_tasks(args.keyword)
        
        elif args.command == 'clear':
            clear_completed_tasks()
        
        elif args.command == 'backup':
            backup_tasks()
        
        elif args.command == 'reset':
            reset_tasks()
        
        elif args.command == 'summary':
            summary()
        
        elif args.command == 'stats':
            stats_tasks()
        
        elif args.command == 'help':
            show_help()
        
        elif args.command == 'version':
            show_version()
        
        else:
            print(f"Unknown command: {args.command}")
            show_help()
    
    except KeyboardInterrupt:
        print("\n\nTaskFlow session ended gracefully.")
        print("Remember: Progress, not perfection. 💫")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        print("Please report this issue if it persists.")
        sys.exit(1)


if __name__ == "__main__":
    main()