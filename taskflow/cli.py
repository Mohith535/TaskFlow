#!/usr/bin/env python3
"""
TaskFlow CLI v2.5
-----------------
Calm, Powerful CLI Task Assistant with Focus Blocking
"""

import sys
import os
import argparse
import difflib

class CustomParser(argparse.ArgumentParser):
    """Custom parser for cleaner errors and fuzzy suggestions."""
    def error(self, message):
        import re
        wrong_cmd = None
        if "invalid choice: '" in message:
            match = re.search(r"invalid choice: '([^']*)'", message)
            if match:
                wrong_cmd = match.group(1)
        
        print(f"\n❌ Unknown command: '{wrong_cmd or 'unknown'}'")
        
        if wrong_cmd:
            # Extract choices from subparsers if they exist
            choices = []
            for action in self._actions:
                if isinstance(action, argparse._SubParsersAction):
                    choices.extend(action.choices.keys())
            
            suggestions = difflib.get_close_matches(wrong_cmd, choices, n=1, cutoff=0.5)
            if suggestions:
                print(f"💡 Did you mean 'taskflow {suggestions[0]}'?\n")
            else:
                print(f"💡 Run 'taskflow help' to see all commands.\n")
        else:
            print(f"💡 Tip: {message}\n")
            
        sys.exit(2)

# Fix for Windows console encoding
if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    os.system('chcp 65001 > nul')  # Set console to UTF-8

from task_manager.commands import (
    add_task,
    change_priority,
    list_ids,
    list_tasks,
    complete_task,
    delete_task,
    rename_task,
    stats_tasks,
    undo_task,
    edit_task,
    search_tasks,
    clear_completed_tasks,
    summary,
    reset_tasks,
    view_task,
    set_prime_target,
    render_timeline,
    # v2.0 time management commands
    focus_task,
    check_focus,
    end_focus,
    schedule_task,
    show_today_tasks,
    add_note,
    edit_note,
    manage_links,
    manage_checklist,
    tag_task,
    backup_tasks,
    # v2.5 focus blocking commands (new!)
    focus_blocking_status,
    test_blocking,
    emergency_cleanup,
    manage_blocklist,
    open_web_ui,
    kill_web_ui,
    dump_task,
    run_today_view,
    command_postpone,
    command_remind,
    command_recover,
    command_missed,
    check_reminders,
    check_recovery_mode
)
from task_manager.storage import storage
import colorama

APP_NAME = "TaskFlow"
APP_VERSION = "v8.5.0"
APP_TAGLINE = "The Execution Engine"


def show_help() -> None:
    """Show comprehensive help with premium formatting."""
    print(f"""
  TaskFlow v8.5.0 — The Execution Engine
  {"─" * 60}

  CORE COMMANDS:
    add                     Add mission interactively
    dump <thought>          Frictionless quick capture (!h !m !l for priority, #tag)
                            PowerShell: quote with "" if using # (e.g. "task #tag !h")
    list                    List your mission board (--todo, --done)
    view <id>               View detailed mission brief
    edit <id>               Recalibrate mission parameters
    complete <id>           Mark mission as [V] SUCCESS
    undo <id>               Re-open mission to [ ] TODO
    delete <id>             Purge mission from record

  CHRONO & TIMELINE (v2.0 / Matrix Sync):
    focus --id <id>         Initiate Focus Flow (default 25m)
    timeline                Render a 7-day tactical terminal view
    prime <id> [date]       Set mission as [PRIME TARGET] for a day
    schedule <id> <date>    Assign mission to timeline (YYYY-MM-DD/today)
    today                   Review missions assigned for today
    missed                  Triage missed missions interactively (--hard/--soft/--skip)
    
  ENHANCED TELEMETRY:
    note <id>               Add/edit mission notes (description)
    link <id>               Manage links & references (--add URL --title)
    check <id> [item]       Manage checklist (item number toggles directly)
    tag <id> <tags...>      Categorize mission (multi-tag support)
    priority <id> <level>   Adjust mission priority (low/medium/high)
    search <keyword>        Query mission database
    summary                 Human-readable mission overview
    stats                   Deep analytical performance metrics

  MAINTENANCE & SAFETY:
    clear                   Prune completed missions
    backup                  Create manual mission database backup
    reset                   Hard reset mission database (Caution!)
    help                    Display this assistance manual
    version                 Show system version
    ui                      Launch the Mission Control Web HUD

  EXAMPLES:
    taskflow add
    taskflow focus --id 7 --minutes 45 --mode strict
    taskflow list --todo --priority high --sort due

  TIPS:
    • Use '--all' with list to see the full mission board
    • Mode 'strict' in focus prevents digital distractions
    • Regular backups ensure mission data integrity
  {"─" * 60}
""")

def show_first_run_wizard():
    """Show first-run wizard for new users (S0-D)."""
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  Welcome to TaskFlow.")
    print("  Built for people who execute,")
    print("  not just organize.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("\n  What's the most important thing")
    print("  you need to do today?\n")
    
    task_title = input("  > ").strip()
    
    if not task_title:
        print("\nSkipping setup. Run 'taskflow add' anytime.")
        print()
        show_help()
    else:
        from task_manager.commands import validate_title
        from task_manager.models import Task, TaskManager
        from datetime import datetime
        
        clean_title = validate_title(task_title)
        if clean_title:
            tasks = storage.load_tasks()
            manager = TaskManager(tasks)
            task = Task(id=0, title=clean_title, priority="High")
            
            # set prime target for today
            today = datetime.now().strftime('%Y-%m-%d')
            task_id = manager.add_task(task)
            storage.save_tasks(manager.tasks)
            
            mapping = storage.load_timeline()
            mapping[str(task_id)] = f"{today}_prime"
            storage.save_timeline(mapping)
            
            print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print("  Mission locked. Set as Prime Target.")
            print("\n  Your three commands:")
            print("  taskflow today    → your execution plan")
            print("  taskflow ui       → open the dashboard")
            print("  taskflow dump \"\"  → capture anything fast")
            print("\n  That's all you need to start.")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
    # Set config flag
    config = storage.load_config()
    config["first_run_complete"] = True
    storage.save_config(config)

def command_doctor():
    """Run full health check report (S0-C)."""
    import platform
    print("\nChecking TaskFlow installation...")
    
    # Python
    py_version = sys.version.split()[0]
    py_major, py_minor = sys.version_info[:2]
    if py_major >= 3 and py_minor >= 10:
        print(f"✓ Python {py_version} detected")
    else:
        print(f"✗ Python {py_version} detected (requires 3.10+)")
        
    # TaskFlow version
    print(f"✓ TaskFlow {APP_VERSION} installed")
    
    # tasks.json
    try:
        tasks = storage.load_tasks()
        print(f"✓ tasks.json found — {len(tasks)} tasks at {storage.tasks_file}")
    except Exception:
        print(f"✗ tasks.json not found or corrupted at {storage.tasks_file}")
        
    # dateparser
    try:
        import dateparser
        dp_ver = getattr(dateparser, '__version__', None) or getattr(dateparser, 'VERSION', 'installed')
        print(f"✓ dateparser {dp_ver} installed")
    except ImportError:
        print("✗ dateparser not installed")
        
    # colorama
    try:
        import colorama
        print(f"✓ colorama {colorama.__version__} installed")
    except ImportError:
        print("✗ colorama not installed")
        
    # Scripts in PATH
    scripts_dir = os.path.dirname(sys.executable)
    if not scripts_dir.endswith("Scripts"):
        scripts_dir = os.path.join(scripts_dir, "Scripts")
    path_env = os.environ.get("PATH", "")
    
    issues = 0
    if scripts_dir.lower() not in path_env.lower():
        print("✗ Scripts not in PATH")
        print(f"  Fix: setx PATH \"%PATH%;{scripts_dir}\"")
        issues += 1
    else:
        print("✓ Scripts directory in PATH")
        
    # Orphaned focus sessions
    try:
        from task_manager.commands import focus_manager
        if focus_manager.is_focus_active():
            print("✗ Orphaned focus session detected")
            issues += 1
        else:
            print("✓ No orphaned focus sessions")
    except Exception:
        print("✓ No orphaned focus sessions")
        
    # Recovery Mode
    rec_state = storage.load_recovery_state()
    if rec_state.get("active"):
        print("✗ Recovery Mode: active")
        issues += 1
    else:
        print("✓ Recovery Mode: inactive")
        
    print(f"\nStatus: {'All systems ready' if issues == 0 else f'{issues} issue(s) found. See fix above.'}\n")

def show_version():
    """Show version information with system details."""
    from pathlib import Path
    
    print(f"\n  🌊 \033[1;36mTaskFlow {APP_VERSION}\033[0m — {APP_TAGLINE}")
    print(f"  \033[90m{'─' * 60}\033[0m")
    
    # System info
    print(f"  \033[1mSYSTEM INFO:\033[0m")
    print(f"  • Python:         {sys.version.split()[0]}")
    print(f"  • Platform:       {sys.platform}")
    data_dir = Path.home() / '.taskflow'
    print(f"  • Data directory:  {data_dir}")
    try:
        tasks = storage.load_tasks()
        total = len(tasks)
        done = sum(1 for t in tasks if t.completed)
        print(f"  • Missions:       {total} total, {done} completed")
    except Exception:
        print(f"  • Missions:       (unable to read)")
    
    print(f"\n  \033[1mWHAT'S NEW IN {APP_VERSION}:\033[0m")
    print("  • \033[33mPhase 1 Complete\033[0m: The full behavioral execution engine")
    print("  • \033[31mRecovery Mode\033[0m: Auto + manual triage with 4 Web HUD entry points")
    print("  • \033[32mSmart Reminders\033[0m: Context-matched timing (priority × deadline type)")
    print("  • \033[36mTask Enrichment\033[0m: Notes, links & checklists on every mission")
    print("  • \033[35mExecution Pressure\033[0m: Live deadline color-shifts (Now Window + today view)")
    print(f"  \033[90m{'─' * 60}\033[0m")
    print("  \033[3mBuilt for deep work. Engineered for execution.\033[0m\n")


def create_parser():
    """Create argparse parser that matches your command structure."""
    parser = CustomParser(
        description=f"{APP_NAME} {APP_VERSION} — {APP_TAGLINE}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  taskflow add
  taskflow list --todo --priority high
  taskflow focus --id 6 --minutes 60 --block-sites facebook.com youtube.com
  taskflow schedule 8 today
  taskflow stats
  taskflow focus-blocking
  taskflow test-blocking --mode gentle
        """,
        add_help=False  # We'll handle help manually
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add command (no arguments - uses interactive input)
    add_parser = subparsers.add_parser('add', help='Add a new task (interactive)')
    add_parser.add_argument('--hard', action='store_true', help='Set hard deadline type')
    add_parser.add_argument('--deadline', type=str, help='Set deadline directly (e.g. "3pm", "tomorrow")')
    add_parser.add_argument('--duration', type=str, help='Set duration directly (e.g. "30m", "1h")')
    add_parser.add_argument('--priority', choices=['low', 'medium', 'high'], help='Set priority directly')
    
    # List command with flags   
    list_parser = subparsers.add_parser('list', help='List tasks with filtering')
    list_parser.add_argument(
        "--sort",
        choices=["priority", "created", "due"],
        help="Sort tasks by priority, creation time, or due date"
    )

    list_parser.add_argument('--todo', action='store_true', help='Show only pending tasks')
    list_parser.add_argument('--done', action='store_true', help='Show only completed tasks')
    list_parser.add_argument('--priority', choices=['low', 'medium', 'high'], 
                           help='Filter by priority')
    list_parser.add_argument('--tag', help='Filter by tag')
    list_parser.add_argument('--all', action='store_true',
                           help='Show all tasks (no 10-task limit)')
    list_parser.add_argument('--detail', action='store_true',
                           help='Show enrichment details (notes preview, links, checklist) under each task')
    
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
    
    # Focus command - UPDATED with blocking options
    focus_parser = subparsers.add_parser('focus', help='Focus session with distraction blocking')
    focus_group = focus_parser.add_mutually_exclusive_group(required=True)
    focus_group.add_argument('--id', type=int, help='Task ID to focus on')
    focus_group.add_argument('--status', action='store_true', help='Check focus status')
    focus_group.add_argument('--end', action='store_true', help='End focus session')
    focus_parser.add_argument('--minutes', type=int, default=25, 
                            help='Focus duration in minutes (default: 25)')
    # NEW: Blocking arguments
    focus_parser.add_argument('--block-sites', nargs='+', 
                            help='Websites to block/avoid (e.g., facebook.com youtube.com)')
    focus_parser.add_argument('--block-apps', nargs='+', 
                            help='Applications to avoid (e.g., discord spotify)')
    focus_parser.add_argument('--mode', choices=['gentle', 'strict'], default='gentle',
                            help='Blocking mode: gentle (reminders) or strict (actual blocking)')
    focus_parser.add_argument('--force', action='store_true', help='Force operation without interactive prompts')
    
    # Priority command
    priority_parser = subparsers.add_parser('priority', help='Change task priority')
    priority_parser.add_argument('id', type=int, help='Task ID')
    priority_parser.add_argument('level', choices=['low', 'medium', 'high'], 
                               help='New priority level')
    
    schedule_parser = subparsers.add_parser('schedule', help='Schedule a task')
    schedule_parser.add_argument('id', type=int, help='Task ID')
    schedule_parser.add_argument('date', help='Date (YYYY-MM-DD, "today", or "tomorrow")')
    
    # Feature 6: Postpone
    postpone_parser = subparsers.add_parser('postpone', help='Proactively postpone a task')
    postpone_parser.add_argument('id', type=int, help='Task ID')
    
    # Feature 7: Remind
    remind_parser = subparsers.add_parser('remind', help='Manage task reminders')
    remind_parser.add_argument('id', type=int, help='Task ID')
    remind_parser.add_argument('--set', dest='set_str', help='Set a new reminder time')
    remind_parser.add_argument('--clear', action='store_true', help='Clear all reminders for this task')
    
    # Feature 9: Recover
    recover_parser = subparsers.add_parser('recover', help='Manage system recovery mode')
    recover_parser.add_argument('--trigger', action='store_true', help='Manually trigger recovery mode')
    recover_parser.add_argument('--exit', action='store_true', help='Exit recovery mode')
    recover_parser.add_argument('--status', action='store_true', help='Show recovery mode status')

    # Missed mission review — the ONLY interactive E/P/D/O flow (user-invoked, escapable)
    missed_parser = subparsers.add_parser('missed', help='Review & address missed missions interactively')
    missed_parser.add_argument('--hard', action='store_true', help='Only HARD missed deadlines')
    missed_parser.add_argument('--soft', action='store_true', help='Only soft missed deadlines')
    missed_parser.add_argument('--skip', action='store_true', help='List missed missions without prompts')
    
    # Timeline
    subparsers.add_parser('timeline', help='Render a 7-day tactical terminal view')
    
    # Prime
    prime_parser = subparsers.add_parser('prime', help='Set task as PRIME TARGET for a day')
    prime_parser.add_argument('id', type=int, help='Task ID')
    prime_parser.add_argument('date', nargs='?', default='today', help='Date (YYYY-MM-DD, "today", or "tomorrow")')
    
    # Tag command
    tag_parser = subparsers.add_parser('tag', help='Add tags to a task')
    tag_parser.add_argument('id', type=int, help='Task ID')
    tag_parser.add_argument('tags', nargs='+', help='Tags to add')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search tasks by keyword')
    search_parser.add_argument('keyword', help='Search keyword')

    # id command
    subparsers.add_parser("ids", help="Show only task IDs")
    
    # NEW: Focus blocking commands
    # Focus blocking status
    blocking_parser = subparsers.add_parser('focus-blocking', 
                                          help='Check blocking system status and what is currently blocked')
    
    # Test blocking system
    test_parser = subparsers.add_parser('test-blocking', 
                                      help='Test the blocking system without starting a focus session')
    test_parser.add_argument('--mode', choices=['gentle', 'strict'], default='gentle',
                           help='Test mode: gentle (reminders) or strict (actual blocking)')
    
    # Blocklist
    blocklist_parser = subparsers.add_parser('blocklist', help='Manage persistent list of blocked websites')
    blocklist_parser.add_argument('--add', nargs='+', help='Websites to add to blocklist')
    blocklist_parser.add_argument('--remove', nargs='+', type=int, help='Indices of websites to remove')
    blocklist_parser.add_argument('--list', action='store_true', help='List all blocked websites')
    blocklist_parser.add_argument('--edit', action='store_true', help='Open blocklist in text editor')
    
    # Emergency cleanup
    subparsers.add_parser('cleanup', 
                         help='Emergency cleanup if blocking gets stuck or system crashes')
                         
    # Frictionless dump
    dump_parser = subparsers.add_parser('dump', help='Frictionless quick capture of a thought')
    dump_parser.add_argument('text', nargs='+', help='The task description string')
    dump_parser.add_argument('--duration', type=str, help='Set duration (e.g. 1h)')
    dump_parser.add_argument('--deadline', type=str, help='Set deadline (e.g. tomorrow 3pm)')
    dump_parser.add_argument('--hard', action='store_true', help='Set deadline type to hard')
    dump_parser.add_argument('--note', type=str, help='Attach a description/note to the task')
    dump_parser.add_argument('--link', action='append', dest='links', metavar='URL',
                             help='Attach a link/reference (auto-detected; repeatable, up to 10)')
    dump_parser.add_argument('--link-title', action='append', dest='link_titles', metavar='TITLE',
                             help='Title for the most recent --link')

    # Link management (E6)
    link_parser = subparsers.add_parser('link', help='View/manage links & references for a task')
    link_parser.add_argument('id', type=int, help='Task ID')
    link_parser.add_argument('--add', type=str, metavar='URL', help='Add a link directly (auto-detects type)')
    link_parser.add_argument('--title', type=str, help='Label for the --add link')

    # Checklist management (E7)
    check_parser = subparsers.add_parser('check', help='View/manage checklist for a task')
    check_parser.add_argument('id', type=int, help='Task ID')
    check_parser.add_argument('item', type=int, nargs='?', default=None,
                              help='Item number to toggle directly (skips the interactive menu)')
    
    # Doctor
    subparsers.add_parser('doctor', help='Check system health')
    
    
    # Simple commands without arguments
    simple_commands = [
        ('today', "Show today's scheduled tasks"),
        ('status', 'Show task list (alias for list)'),
        ('stats', 'Show task statistics'),
        ('summary', 'Human-readable summary'),
        ('backup', 'Create manual backup'),
        ('clear', 'Clear completed tasks'),
        ('reset', 'Reset all tasks (with confirmation)'),
        ('version', 'Show version information'),
        ('help', 'Show help message'),
        ('ui', 'Launch the Developer Web Dashboard'),
        ('ui-kill', 'Kill any running Web UI server')
    ]
    
    for cmd, help_text in simple_commands:
        p = subparsers.add_parser(cmd, help=help_text)
        if cmd == 'ui':
            p.add_argument('--restart', '-r', action='store_true', help='Force restart the server')
    
    return parser


def main():
    """Main command router using argparse with startup cleanup."""
    
    # Add this at the VERY beginning of main() to cleanup orphaned blocks
    try:
        from task_manager.system_detector import SystemDetector
        from task_manager.blockers.windows import WindowsBlocker
        from task_manager.commands import time_tracker
        
        # Colorama init
        colorama.init(autoreset=True)
        
        # S0-B: Path detection
        scripts_dir = os.path.dirname(sys.executable)
        if not scripts_dir.endswith("Scripts"):
            scripts_dir = os.path.join(scripts_dir, "Scripts")
        path_env = os.environ.get("PATH", "")
        
        config = storage.load_config()
        if scripts_dir.lower() not in path_env.lower() and not config.get("path_warning_shown"):
            print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print("taskflow is installed but not in PATH.")
            print("Run this once to fix it permanently:\n")
            print("Windows CMD:")
            print(f"setx PATH \"%PATH%;{scripts_dir}\"\n")
            print("Then restart your terminal and run: taskflow")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
            config["path_warning_shown"] = True
            storage.save_config(config)
            
        # If on Windows and admin, check for orphaned blocks IF no active session
        if SystemDetector.get_os() == "windows" and SystemDetector.is_admin():
            if not time_tracker.active_session:
                checker = WindowsBlocker()
                # This will silently clean up if there are orphaned blocks
                with open(checker.hosts_path, 'r') as f:
                    if "# TaskFlow Focus Mode" in f.read():
                        print("🔍 Checking for orphaned focus blocks...")
                        checker.unblock_websites()
    except Exception as e:
        pass  # Don't crash on startup
        
    parser = create_parser()
    
    # Show help if no arguments (or welcome for first-run)
    if len(sys.argv) == 1:
        config = storage.load_config()
        if not config.get("first_run_complete"):
            show_first_run_wizard()
        else:
            show_help()
        return
    
    # Special case: help command
    if sys.argv[1] in ['help', '--help', '-h']:
        show_help()
        return
    
    try:
        args = parser.parse_args()
    except SystemExit as e:
        # If it's a normal exit (e.g. --help), just exit
        if e.code == 0:
            sys.exit(0)
        # CustomParser.error already printed the message and will exit with code 2
        return
    
    # If no command specified, show help
    if not hasattr(args, 'command') or args.command is None:
        show_help()
        return
    
    # Route commands
    try:
        # STARTUP HOOKS — S7 (reminders) + S9 (recovery)
        # S7-D: reminders fire at the start of EVERY command (silent if none due)
        if getattr(args, 'command', None):
            try:
                check_reminders(storage.load_tasks())
            except Exception:
                pass
        # S9-D: recovery check intercepts the read views only
        if args.command in ['list', 'status', 'today']:
            if check_recovery_mode():
                # Intercept normal views if recovery mode is active
                args.command = 'recover'
                
        if args.command == 'add':
            add_task(
                is_hard=getattr(args, 'hard', False),
                preset_deadline=getattr(args, 'deadline', None),
                preset_duration=getattr(args, 'duration', None),
                preset_priority=getattr(args, 'priority', None)
            )
        
        elif args.command in ['list', 'status']:
            # Standard CLI List
            filter_status = None
            if args.todo:
                filter_status = 'todo'
            elif args.done:
                filter_status = 'done'
            
            list_tasks(
                filter_status=filter_status,
                filter_priority=args.priority,
                filter_tag=args.tag,
                show_all=args.all,
                sort_by=args.sort,
                show_detail=getattr(args, 'detail', False)
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
            edit_note(args.id)
        
        elif args.command == 'focus':
            if args.status:
                check_focus()
            elif args.end:
                end_focus(force=args.force)
            elif args.id:
                # UPDATED: Pass all blocking arguments
                focus_task(
                    task_id=args.id,
                    minutes=args.minutes,
                    block_sites=args.block_sites,
                    block_apps=args.block_apps,
                    mode=args.mode
                )
            else:
                print("Use: taskflow focus --id 6 [--minutes 25]")
                print("     taskflow focus --status")
                print("     taskflow focus --end")
                print("\nBlocking options:")
                print("  --block-sites facebook.com youtube.com")
                print("  --block-apps discord spotify")
                print("  --mode gentle/strict")
        
        elif args.command == 'priority':
            change_priority(args.id, args.level)
        
        elif args.command == 'schedule':
            schedule_task(args.id, args.date)
            
        elif args.command == 'prime':
            set_prime_target(args.id, args.date)
            
        elif args.command == 'timeline':
            render_timeline()
        
        elif args.command == 'today':
            run_today_view()
        
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
            
        elif args.command == 'ui':
            open_web_ui(force=args.restart)

        elif args.command == 'ui-kill':
            kill_web_ui()

        elif args.command == "ids":
            list_ids()
        
        # NEW: Focus blocking commands
        elif args.command == 'blocklist':
            if args.add:
                manage_blocklist("add", sites=args.add)
            elif args.remove:
                manage_blocklist("remove", indices=args.remove)
            elif args.edit:
                manage_blocklist("edit")
            else:
                manage_blocklist("list")

        elif args.command == 'focus-blocking':
            focus_blocking_status()
        
        elif args.command == 'test-blocking':
            test_blocking(args.mode)
        
        elif args.command == 'cleanup':
            emergency_cleanup()
            
        elif args.command == 'dump':
            if args.text:
                text = " ".join(args.text)
                # E3: assemble --link / --link-title into link dicts (positional pairing)
                dump_links = None
                raw_links = getattr(args, 'links', None)
                if raw_links:
                    titles = getattr(args, 'link_titles', None) or []
                    dump_links = []
                    for i, url in enumerate(raw_links):
                        dump_links.append({
                            "url": url,
                            "title": titles[i] if i < len(titles) else None
                        })
                dump_task(
                    text,
                    duration=args.duration,
                    deadline=args.deadline,
                    is_hard=args.hard,
                    note=getattr(args, 'note', None),
                    links=dump_links
                )
            else:
                Messenger.careful("No text provided for dump.")

        elif args.command == 'link':
            manage_links(args.id, add_url=getattr(args, 'add', None), title=getattr(args, 'title', None))

        elif args.command == 'check':
            manage_checklist(args.id, toggle_index=getattr(args, 'item', None))
                
        elif args.command == 'doctor':
            command_doctor()
                
        elif args.command == 'postpone':
            command_postpone(args.id)
            
        elif args.command == 'remind':
            command_remind(args.id, args.set_str, args.clear)
            
        elif args.command == 'recover':
            command_recover(
                trigger=getattr(args, 'trigger', False),
                exit_mode=getattr(args, 'exit', False),
                status=getattr(args, 'status', False)
            )

        elif args.command == 'missed':
            command_missed(
                hard_only=getattr(args, 'hard', False),
                soft_only=getattr(args, 'soft', False),
                skip_list=getattr(args, 'skip', False)
            )
        
        else:
            print(f"Unknown command: {args.command}")
            show_help()
    
    except KeyboardInterrupt:
        print("\n\nTaskFlow session ended gracefully.")
        print("Remember: Progress, not perfection. 💫")
        sys.exit(0) 
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nAn unexpected error occurred: {e}")
        print("Please report this issue if it persists.")
        sys.exit(1)


if __name__ == "__main__":
    main()