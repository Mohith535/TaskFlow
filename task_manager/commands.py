"""
TaskFlow Commands Module v2.0 - Complete Version
------------------------------------------------
All functions for main.py imports + v2.0 time management features.
"""

from task_manager.storage import storage
from task_manager.models import Task, TaskManager
from datetime import datetime, timedelta
import time
import sys
from typing import Optional, List
import json
from pathlib import Path


# =========================================================
# CONFIGURATION
# =========================================================

COL_WIDTHS = {
    "id": 4,
    "status": 6,
    "title": 30,
    "priority": 8,
    "tags": 15,
    "created": 12,
    "completed": 12
}

MAX_VISIBLE_TASKS = 10
FOCUS_SESSION_MINUTES = 25  # Default Pomodoro session


# =========================================================
# MESSAGE HELPERS (Enhanced with emotional intelligence)
# =========================================================

class Messenger:
    """Unified message formatting with emotional awareness."""
    
    @staticmethod
    def info(msg: str):
        print(f"Info: {msg}")
    
    @staticmethod
    def note(msg: str):
        print(f"Note: {msg}")
    
    @staticmethod
    def success(msg: str):
        print(f"OK: {msg}")
    
    @staticmethod
    def careful(msg: str):
        print(f"Careful: {msg}")
    
    @staticmethod
    def task_not_found(task_id: int):
        Messenger.info(f"Task {task_id} isn't available right now.")
    
    @staticmethod
    def empty_list():
        Messenger.note("Your task list is empty. A good place to start.")
    
    @staticmethod
    def no_pending_tasks():
        Messenger.note("No pending tasks. Everything is completed.")
        Messenger.note("You're clear for now. Take a breath.")
    
    @staticmethod
    def focus_start(task_title: str, minutes: int):
        print(f"\n🔥 Starting focus session for {minutes} minutes")
        print(f"📝 Task: {task_title}")
        print("⏰ Focus until:", (datetime.now() + timedelta(minutes=minutes)).strftime("%H:%M"))
    
    @staticmethod
    def focus_complete(task_title: str, minutes: int = 25):
        print(f"\n✅ {minutes}min session completed!")
        print(f"✨ Great work on: {task_title}")
        print("💫 Take a short break before continuing.")


# =========================================================
# INPUT VALIDATION
# =========================================================

def validate_title(title: str) -> Optional[str]:
    """Validate task title."""
    title = title.strip()
    if not title:
        Messenger.careful("Task title cannot be empty.")
        return None
    if len(title) > 200:
        Messenger.careful("Title is too long (max 200 characters).")
        return None
    return title


def get_valid_input(prompt: str, default: str = "") -> str:
    """Get validated user input with optional default."""
    try:
        response = input(prompt).strip()
        return response if response else default
    except (EOFError, KeyboardInterrupt):
        print()  # Clean line break
        return ""


def confirm_action(message: str) -> bool:
    """Get confirmation for destructive actions."""
    response = get_valid_input(f"{message} (y/N): ").lower()
    return response == 'y'


# =========================================================
# TIME MANAGEMENT UTILITIES
# =========================================================

class TimeTracker:
    """Track time spent on tasks."""
    def __init__(self):
        self.active_session = None
        self.start_time = None

    def start_focus(self, task_id: int, task_title: str, minutes: int = 25):
        """Start a focus session for a task."""
        self.active_session = {
            'task_id': task_id,
            'task_title': task_title,
            'minutes': minutes,
            'start_time': datetime.now()
        }
        self.start_time = time.time()
        Messenger.focus_start(task_title, minutes)
        return self.active_session

    def check_focus() -> None:
        """Check current focus session status."""
        status = time_tracker.check_focus()
        
        if not status:
            Messenger.note("No active focus session.")
            return
        
        if status['status'] == 'active':
            print(f"\n🔥 Focus session active")
            print(f"⏱️  Elapsed: {status['elapsed_minutes']}m {status.get('remaining_seconds', 0)}s")
            print(f"⏱️  Remaining: {status['remaining_minutes']}m {status.get('remaining_seconds', 0)}s")
            print(f"📝 Task: {time_tracker.active_session['task_title']}")
        else:
            Messenger.success("Focus session completed!")

    def end_focus(self):
        """End current focus session."""
        if self.active_session:
            # Add focus time to task
            try:
                tasks = storage.load_tasks()
                for task in tasks:
                    if task.id == self.active_session['task_id']:
                        task.add_focus_minutes(self.active_session['minutes'])
                        storage.save_tasks(tasks)
                        break
            except Exception:
                pass  # Don't crash if can't save focus time
            
            # FIXED: Use actual minutes from session
            actual_minutes = self.active_session['minutes']
            Messenger.focus_complete(self.active_session['task_title'], actual_minutes)
            self.active_session = None
            self.start_time = None
        
        # Clear saved state
        self._save_state({'active_session': None, 'start_time': None})

class TimeTracker:
    """Track time spent on tasks."""
    
    def __init__(self):
        self.active_session = None
        self.start_time = None
        self._load_state()
    
    def _load_state(self):
        """Load saved focus state from disk."""
        try:
            state_file = Path(".taskflow/focus_state.json")
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    
                    # Check if we have an active session
                    if state.get('active_session'):
                        # Convert string time back to datetime
                        start_time_str = state['active_session']['start_time']
                        start_time = datetime.fromisoformat(start_time_str)
                        minutes = state['active_session']['minutes']
                        
                        # Calculate elapsed time
                        elapsed = (datetime.now() - start_time).total_seconds()
                        remaining = (minutes * 60) - elapsed
                        
                        if remaining > 0:
                            # Session still active - restore it
                            self.active_session = state['active_session']
                            self.start_time = time.time() - elapsed
                            # REMOVED the print statement here to avoid spam
                        else:
                            # Session expired - auto-end it
                            print(f"⏰ Previous focus session expired.")
                            self._save_state({'active_session': None, 'start_time': None})
                    else:
                        # No active session - ensure clean state
                        self.active_session = None
                        self.start_time = None
        except (json.JSONDecodeError, FileNotFoundError, KeyError, ValueError):
            # If any error, start fresh
            self.active_session = None
            self.start_time = None
    
    def _save_state(self, state=None):
        """Save focus state to disk."""
        try:
            state_file = Path(".taskflow/focus_state.json")
            state_file.parent.mkdir(parents=True, exist_ok=True)
            
            if state is None:
                state = {
                    'active_session': self.active_session,
                    'start_time': self.start_time,
                    'saved_at': datetime.now().isoformat()
                }
            
            with open(state_file, 'w') as f:
                json.dump(state, f)
        except Exception:
            pass  # Silent fail for focus state
    
    def start_focus(self, task_id: int, task_title: str, minutes: int = 25):
        """Start a focus session for a task."""
        self.active_session = {
            'task_id': task_id,
            'task_title': task_title,
            'minutes': minutes,
            'start_time': datetime.now().isoformat()
        }
        self.start_time = time.time()
        
        # Save immediately
        self._save_state()
        
        Messenger.focus_start(task_title, minutes)
        return self.active_session
    
    def check_focus(self):
        """Check current focus session status."""
        if not self.active_session:
            return None
        
        elapsed = time.time() - self.start_time
        remaining = (self.active_session['minutes'] * 60) - elapsed
        
        if remaining <= 0:
            # Session completed naturally
            session = self.active_session.copy()
            self.end_focus()
            return {'status': 'completed', 'session': session}
        
        return {
            'status': 'active',
            'elapsed_minutes': int(elapsed / 60),
            'remaining_minutes': int(remaining / 60),
            'remaining_seconds': int(remaining % 60)
        }
    
    def end_focus(self):
        """End current focus session."""
        if not self.active_session:
            Messenger.note("No active focus session to end.")
            return
        
        try:
            # Add focus time to task
            tasks = storage.load_tasks()
            session_minutes = self.active_session['minutes']
            task_title = self.active_session['task_title']
            
            for task in tasks:
                if task.id == self.active_session['task_id']:
                    task.add_focus_minutes(session_minutes)
                    storage.save_tasks(tasks)
                    break
        except Exception:
            pass  # Don't crash if can't save focus time
        
        # Show completion message
        Messenger.focus_complete(task_title, session_minutes)
        
        # Clear session
        self.active_session = None
        self.start_time = None
        
        # Clear saved state
        self._save_state({'active_session': None, 'start_time': None})
        print("🧹 Focus session cleared from memory.")


# Global instance
time_tracker = TimeTracker()



# =========================================================
# CORE TASK OPERATIONS (Enhanced) - MAIN.PY IMPORTS THESE
# =========================================================

def add_task() -> bool:
    """Add a new task with improved UX."""
    tasks = storage.load_tasks()
    manager = TaskManager(tasks)
    
    title = get_valid_input("Task title: ")
    title = validate_title(title)
    if not title:
        return False
    
    priority_input = get_valid_input("Priority (Low/Medium/High) [Medium]: ", "Medium")
    priority = normalize_priority(priority_input)
    
    # Ask for tags
    tags_input = get_valid_input("Tags (comma-separated, optional): ")
    tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
    
    task = Task(
        id=0,  # Will be auto-assigned
        title=title,
        priority=priority,
        tags=tags
    )
    
    try:
        task_id = manager.add_task(task)
        storage.save_tasks(manager.tasks)
        Messenger.success(f"Task #{task_id} added successfully.")
        return True
    except Exception as e:
        Messenger.careful(f"Could not add task: {e}")
        return False


def list_tasks(filter_status: Optional[str] = None, 
               filter_priority: Optional[str] = None,
               filter_tag: Optional[str] = None,
               show_all: bool = False) -> None:
    """List tasks with advanced filtering."""
    tasks = storage.load_tasks()
    
    if not tasks:
        Messenger.empty_list()
        return
    
    # Apply filters
    filtered_tasks = []
    for task in tasks:
        # Status filter
        if filter_status == "todo" and task.completed:
            continue
        if filter_status == "done" and not task.completed:
            continue
        
        # Priority filter
        if filter_priority and task.priority.lower() != filter_priority.lower():
            continue
        
        # Tag filter
        if filter_tag and filter_tag not in task.tags:
            continue
        
        filtered_tasks.append(task)
    
    if not filtered_tasks:
        if filter_status == "done":
            Messenger.note("You haven't completed any tasks yet.")
        elif filter_status == "todo":
            Messenger.no_pending_tasks()
        else:
            Messenger.note("No tasks match your filters.")
        return
    
    # Display
    print(f"\n{'ID':<{COL_WIDTHS['id']}} | "
          f"{'STATUS':<{COL_WIDTHS['status']}} | "
          f"{'TITLE':<{COL_WIDTHS['title']}} | "
          f"{'PRIORITY':<{COL_WIDTHS['priority']}} | "
          f"{'TAGS':<{COL_WIDTHS['tags']}}")
    
    separator = "-" * (sum(COL_WIDTHS.values()) + 15)
    print(separator)
    
    shown = 0
    for task in filtered_tasks:
        if not show_all and shown >= MAX_VISIBLE_TASKS:
            Messenger.note(f"Showing first {MAX_VISIBLE_TASKS} tasks. Use '--all' to view everything.")
            break
        
        status = "DONE" if task.completed else "TODO"
        tags_display = ", ".join(task.tags[:2]) + ("..." if len(task.tags) > 2 else "")
        
        print(f"{task.id:<{COL_WIDTHS['id']}} | "
              f"{status:<{COL_WIDTHS['status']}} | "
              f"{task.title[:COL_WIDTHS['title']]:<{COL_WIDTHS['title']}} | "
              f"{task.priority:<{COL_WIDTHS['priority']}} | "
              f"{tags_display:<{COL_WIDTHS['tags']}}")
        shown += 1
    
    print(f"\nTotal: {len(filtered_tasks)} task(s)")


def complete_task(task_id: int) -> bool:
    """Mark a task as completed."""
    tasks = storage.load_tasks()
    
    for task in tasks:
        if task.id == task_id:
            if task.completed:
                Messenger.info(f"Task {task_id} is already completed.")
                return True
            
            task.completed = True
            task.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            storage.save_tasks(tasks)
            Messenger.success(f"Task #{task_id} marked as completed.")
            Messenger.note("Nice progress. One step at a time.")
            return True
    
    Messenger.task_not_found(task_id)
    return False


def delete_task(task_id: int) -> bool:
    """Delete a task."""
    tasks = storage.load_tasks()
    
    for task in tasks:
        if task.id == task_id:
            tasks.remove(task)
            storage.save_tasks(tasks)
            Messenger.success(f"Task #{task_id} removed successfully.")
            return True
    
    Messenger.task_not_found(task_id)
    return False


def rename_task(task_id: int) -> bool:
    """Rename a task (simplified version of edit)."""
    tasks = storage.load_tasks()
    
    for task in tasks:
        if task.id == task_id:
            new_title = get_valid_input(f"New title for task #{task_id}: ")
            new_title = validate_title(new_title)
            if not new_title:
                return False
            
            task.title = new_title
            storage.save_tasks(tasks)
            Messenger.success(f"Task #{task_id} renamed.")
            return True
    
    Messenger.task_not_found(task_id)
    return False


def stats_tasks() -> None:
    """Show detailed statistics with focus minutes."""
    tasks = storage.load_tasks()
    manager = TaskManager(tasks)
    stats = manager.get_stats()
    
    print(f"\n{'='*40}")
    print("TASK STATISTICS")
    print(f"{'='*40}")
    print(f"Total tasks    : {stats['total']}")
    print(f"Completed      : {stats['completed']}")
    print(f"Pending        : {stats['pending']}")
    
    if stats['total'] > 0:
        print(f"Completion rate: {stats['completion_rate']:.1f}%")
        print(f"Total focus time: {stats['total_focus_minutes']} minutes")  # NEW
        print(f"\nPriority Distribution:")
        print(f"  High   : {stats['priorities']['High']:3d} ({stats['priorities']['High']/stats['total']*100:.1f}%)")
        print(f"  Medium : {stats['priorities']['Medium']:3d} ({stats['priorities']['Medium']/stats['total']*100:.1f}%)")
        print(f"  Low    : {stats['priorities']['Low']:3d} ({stats['priorities']['Low']/stats['total']*100:.1f}%)")
    
    print(f"{'='*40}")


def show_help() -> None:
    """Show comprehensive help."""
    print(f"""
TaskFlow v2.0 — Calm, Powerful CLI Task Assistant
{'='*50}

CORE TASK MANAGEMENT:
  add                     Add a new task (interactive)
  list                    List all tasks
  list --todo             List pending tasks
  list --done             List completed tasks
  view <id>               View task details
  edit <id>               Edit task (all fields)
  rename <id>             Rename a task
  complete <id>           Mark task as completed
  undo <id>               Move task back to TODO
  delete <id>             Delete a task

TIME & FOCUS MANAGEMENT (v2.0):
  focus --id <id> [--minutes N]  Start focus session (default: 25 min)
  focus --status            Check focus session
  focus --end               End current focus
  schedule <id> <date>      Schedule task (YYYY-MM-DD/today/tomorrow)
  today                     Show today's scheduled tasks

ENHANCED FEATURES:
  note <id>                 Add/update notes
  tag <id> <tag1> [tag2]    Add tags to task
  priority <id> <level>     Change priority (low/medium/high)
  search <keyword>          Search tasks
  summary                   Human-readable summary
  stats                     Detailed statistics

SAFETY & MAINTENANCE:
  clear                     Clear completed tasks
  backup                    Create manual backup
  reset                     Reset all tasks (with confirmation)
  help                      Show this help
  version                   Show version

EXAMPLES:
  taskflow add
  taskflow list --todo --priority high
  taskflow focus --id 15 --minutes 30
  taskflow schedule 8 today
  taskflow tag 3 work project-x

TIPS:
  • Use '--all' with list to see all tasks
  • Tags help organize related tasks
  • Schedule tasks for better planning
  • Regular backups keep your data safe
""")


def undo_task(task_id: int) -> bool:
    """Move task back to TODO."""
    tasks = storage.load_tasks()
    
    for task in tasks:
        if task.id == task_id:
            if not task.completed:
                Messenger.info(f"Task {task_id} is already TODO.")
                return True
            
            task.completed = False
            task.completed_at = None
            storage.save_tasks(tasks)
            Messenger.success(f"Task #{task_id} moved back to TODO.")
            return True
    
    Messenger.task_not_found(task_id)
    return False


def edit_task(task_id: int) -> bool:
    """Edit a task."""
    tasks = storage.load_tasks()
    
    for task in tasks:
        if task.id == task_id:
            print(f"\nEditing Task #{task_id}: {task.title}")
            print("(Press Enter to keep current value)")
            
            new_title = get_valid_input(f"Title [{task.title}]: ", task.title)
            new_title = validate_title(new_title)
            if not new_title:
                return False
            
            task.title = new_title
            
            new_priority = get_valid_input(f"Priority (L/M/H) [{task.priority[0]}]: ", task.priority[0])
            task.priority = normalize_priority(new_priority)
            
            storage.save_tasks(tasks)
            Messenger.success(f"Task #{task_id} updated successfully.")
            return True
    
    Messenger.task_not_found(task_id)
    return False


def search_tasks(keyword: str) -> None:
    """Search tasks by keyword."""
    tasks = storage.load_tasks()
    
    matches = [
        task for task in tasks
        if keyword.lower() in task.title.lower()
    ]
    
    if not matches:
        Messenger.note("No matching tasks found.")
        return
    
    print(f"\n{'ID':<{COL_WIDTHS['id']}} | "
          f"{'STATUS':<{COL_WIDTHS['status']}} | "
          f"{'TITLE':<{COL_WIDTHS['title']}} | "
          f"{'PRIORITY':<{COL_WIDTHS['priority']}}")
    
    separator = "-" * (COL_WIDTHS['id'] + COL_WIDTHS['status'] + 
                      COL_WIDTHS['title'] + COL_WIDTHS['priority'] + 15)
    print(separator)
    
    for task in matches:
        status = "DONE" if task.completed else "TODO"
        print(f"{task.id:<{COL_WIDTHS['id']}} | "
              f"{status:<{COL_WIDTHS['status']}} | "
              f"{task.title:<{COL_WIDTHS['title']}} | "
              f"{task.priority:<{COL_WIDTHS['priority']}}")


def clear_completed_tasks() -> bool:
    """Clear completed tasks with confirmation."""
    tasks = storage.load_tasks()
    completed = [t for t in tasks if t.completed]
    
    if not completed:
        Messenger.note("No completed tasks to clear.")
        return False
    
    if not confirm_action(f"This will delete {len(completed)} completed task(s)"):
        Messenger.info("Operation cancelled.")
        return False
    
    tasks = [t for t in tasks if not t.completed]
    storage.save_tasks(tasks)
    Messenger.success(f"Cleared {len(completed)} completed task(s).")
    return True


def summary() -> None:
    """Show human-readable summary with encouragement."""
    tasks = storage.load_tasks()
    manager = TaskManager(tasks)
    stats = manager.get_stats()
    
    print(f"\n{'='*40}")
    print("TASKFLOW SUMMARY")
    print(f"{'='*40}")
    print(f"You have {stats['total']} total task(s)")
    print(f"Completed: {stats['completed']}")
    print(f"Pending: {stats['pending']}")
    print(f"Total focus time: {stats['total_focus_minutes']} minutes")  # NEW
    
    if stats['total'] > 0:
        high_pending = sum(1 for t in tasks if not t.completed and t.priority == "High")
        print(f"High priority pending: {high_pending}")
    
    Messenger.note("Keep going, one step at a time!")
    Messenger.note("Consistency matters more than speed.")


def reset_tasks() -> bool:
    """Reset all tasks with strong confirmation."""
    tasks = storage.load_tasks()
    
    if not tasks:
        Messenger.note("No tasks to reset.")
        return False
    
    confirm = get_valid_input(
        "This will delete ALL tasks permanently.\nType RESET to confirm: "
    ).strip()
    
    if confirm != "RESET":
        Messenger.info("Reset cancelled.")
        return False
    
    storage.save_tasks([])
    Messenger.success("All tasks have been cleared.")
    Messenger.note("Fresh start. Nothing lost — only space created.")
    return True


def view_task(task_id: int) -> None:
    """View task details with notes, tags, AND focus minutes."""
    tasks = storage.load_tasks()
    
    for task in tasks:
        if task.id == task_id:
            print(f"\n{'='*40}")
            print(f"TASK #{task_id}")
            print(f"{'='*40}")
            print(f"Title     : {task.title}")
            print(f"Status    : {'COMPLETED' if task.completed else 'PENDING'}")
            print(f"Priority  : {task.priority}")
            print(f"Created   : {task.created_at}")
            print(f"Completed : {task.completed_at or 'Not yet'}")
            print(f"Tags      : {', '.join(task.tags) if task.tags else 'None'}")
            print(f"Notes     : {task.notes or 'No notes yet'}")
            print(f"Focus spent: {task.focus_minutes_spent} minutes")  # NEW LINE
            print(f"{'='*40}")
            return
    
    Messenger.task_not_found(task_id)


def change_priority(task_id: int, level: str) -> bool:
    """Change task priority."""
    tasks = storage.load_tasks()
    priority = normalize_priority(level)
    
    for task in tasks:
        if task.id == task_id:
            task.priority = priority
            storage.save_tasks(tasks)
            Messenger.success(f"Priority updated to {priority}.")
            return True
    
    Messenger.task_not_found(task_id)
    return False


# =========================================================
# TIME MANAGEMENT COMMANDS (NEW for v2.0)
# =========================================================

def focus_task(task_id: int, minutes: int = 25) -> bool:
    """Start a focus session on a specific task."""
    tasks = storage.load_tasks()
    
    for task in tasks:
        if task.id == task_id:
            if task.completed:
                Messenger.note("This task is already completed.")
                return False
            
            # Record focus minutes when session starts
            task.add_focus_minutes(minutes)
            storage.save_tasks(tasks)
            
            time_tracker.start_focus(task_id, task.title, minutes)
            return True
    
    Messenger.task_not_found(task_id)
    return False


def check_focus() -> None:
    """Check current focus session status."""
    status = time_tracker.check_focus()
    
    if not status:
        Messenger.note("No active focus session.")
        return
    
    if status['status'] == 'active':
        print(f"\nFocus session active")
        print(f"Elapsed: {status['elapsed_minutes']} minutes")
        print(f"Remaining: {status['remaining_minutes']} minutes")
    else:
        Messenger.success("Focus session completed!")


def end_focus() -> None:
    """End current focus session."""
    time_tracker.end_focus()


def schedule_task(task_id: int, date_str: str) -> bool:
    """Schedule a task for a specific date."""
    tasks = storage.load_tasks()
    
    try:
        # Parse date (accepts YYYY-MM-DD or relative dates)
        if date_str.lower() in ['today', 'tomorrow']:
            if date_str.lower() == 'today':
                scheduled_date = datetime.now().strftime("%Y-%m-%d")
            else:
                scheduled_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            # Try to parse as YYYY-MM-DD
            datetime.strptime(date_str, "%Y-%m-%d")
            scheduled_date = date_str
        
        for task in tasks:
            if task.id == task_id:
                # Add schedule note
                task.notes = f"[Scheduled: {scheduled_date}] " + (task.notes or "")
                storage.save_tasks(tasks)
                Messenger.success(f"Task #{task_id} scheduled for {scheduled_date}")
                return True
        
        Messenger.task_not_found(task_id)
        return False
        
    except ValueError:
        Messenger.careful("Invalid date format. Use YYYY-MM-DD, 'today', or 'tomorrow'.")
        return False


def show_today_tasks() -> None:
    """Show today's scheduled tasks."""
    today = datetime.now().strftime("%Y-%m-%d")
    tasks = storage.load_tasks()
    
    today_tasks = []
    for task in tasks:
        if f"[Scheduled: {today}]" in (task.notes or ""):
            today_tasks.append(task)
    
    if today_tasks:
        print(f"\n📅 Today's Tasks ({datetime.now().strftime('%A, %b %d')}):")
        for task in today_tasks:
            print(f"  {task}")
    else:
        Messenger.note(f"No tasks scheduled for today ({datetime.now().strftime('%A, %b %d')}).")


# =========================================================
# ENHANCED TASK OPERATIONS (v2.0 extras)
# =========================================================

def add_note(task_id: int) -> bool:
    """Add or update notes for a task."""
    tasks = storage.load_tasks()
    
    for task in tasks:
        if task.id == task_id:
            print(f"\nCurrent notes: {task.notes or 'None'}")
            new_note = get_valid_input("New notes: ")
            task.notes = new_note
            storage.save_tasks(tasks)
            Messenger.success(f"Notes updated for task #{task_id}.")
            return True
    
    Messenger.task_not_found(task_id)
    return False


def tag_task(task_id: int, tags: List[str]) -> bool:
    """Add tags to a task."""
    tasks = storage.load_tasks()
    
    for task in tasks:
        if task.id == task_id:
            for tag in tags:
                if tag not in task.tags:
                    task.tags.append(tag)
            storage.save_tasks(tasks)
            Messenger.success(f"Tags added to task #{task_id}.")
            return True
    
    Messenger.task_not_found(task_id)
    return False


def backup_tasks() -> bool:
    """Create a manual backup."""
    backups = storage.get_backup_list()
    if storage.save_tasks(storage.load_tasks()):  # Triggers backup
        Messenger.success(f"Backup created. Total backups: {len(backups) + 1}")
        return True
    return False


# =========================================================
# UTILITY FUNCTIONS
# =========================================================

def normalize_priority(priority: str) -> str:
    """Normalize priority input to Low / Medium / High."""
    if not priority:
        return "Medium"
    
    priority = priority.strip().lower()
    
    priority_map = {
        'high': 'High', 'h': 'High',
        'medium': 'Medium', 'm': 'Medium',
        'low': 'Low', 'l': 'Low'
    }
    
    return priority_map.get(priority, 'Medium')