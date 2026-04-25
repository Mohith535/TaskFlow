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
import threading
import time
from datetime import datetime
import dateparser
import warnings
warnings.filterwarnings("ignore", module="dateparser")
from colorama import Fore, Style
from .system_detector import SystemDetector
from .blockers import GentleBlocker  # For fallback
from .blockers.blocklist import blocklist_manager

def parse_deadline(raw_string: str):
    """Parse natural language date/time strings."""
    if not raw_string or not raw_string.strip():
        return None
        
    import re
    # Convert "monday 17h" to "monday 17:00" but leave "in 2h" alone
    processed_string = re.sub(r'(?<!in )(?<!\+)\b(\d{1,2})h\b', r'\1:00', raw_string.lower())
    
    return dateparser.parse(
        processed_string,
        settings={
            'PREFER_DATES_FROM': 'future',
            'PREFER_DAY_OF_MONTH': 'first',
            'DATE_ORDER': 'DMY'
        }
    )

def handle_missed_tasks():
    """Handle tasks with missed deadlines using decision pressure."""
    try:
        tasks = storage.load_tasks()
    except Exception:
        return
        
    today_str = datetime.now().strftime('%Y-%m-%d')
    now = datetime.now()
    
    missed_tasks = []
    for task in tasks:
        if task.completed or task.dropped_at or task.offloaded_at:
            continue
        if not task.deadline:
            continue
        try:
            deadline_dt = datetime.fromisoformat(task.deadline)
            if deadline_dt < now and task.last_missed_prompt != today_str:
                missed_tasks.append(task)
        except ValueError:
            pass
            
    if not missed_tasks:
        return
        
    # Sort: HARD first, then SOFT (by deadline)
    def sort_key(t):
        try:
            dt = datetime.fromisoformat(t.deadline)
        except ValueError:
            dt = datetime.max
        return (0 if t.deadline_type == "hard" else 1, dt)
        
    missed_tasks.sort(key=sort_key)
    
    print(Fore.YELLOW + f"You have {len(missed_tasks)} missed mission(s) to address." + Style.RESET_ALL)
    
    for task in missed_tasks:
        try:
            deadline_dt = datetime.fromisoformat(task.deadline)
            due_str = deadline_dt.strftime('%A, %d %b at %I:%M %p')
        except ValueError:
            due_str = task.deadline
            
        print(Fore.YELLOW + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" + Style.RESET_ALL)
        print(Fore.YELLOW + "⚠  Mission window missed" + Style.RESET_ALL)
        print(Fore.YELLOW + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" + Style.RESET_ALL)
        print(f"Task:    " + Fore.WHITE + Style.BRIGHT + task.title + Style.RESET_ALL)
        print(f"Was due: {due_str}")
        print(f"Priority: {task.priority}  ·  Duration: {task.duration or 'None'}")
        print(Fore.YELLOW + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" + Style.RESET_ALL)
        while True:
            print("What do you want to do?\n")
            print("[E]  Execute now     — mark as active, start tracking")
            if task.postpone_count < 5:
                print("[P]  Postpone        — reschedule to a new time")
            print("[D]  Drop            — remove from active tasks")
            print("[O]  Offload         — not my responsibility anymore\n")
            
            choice = get_valid_input("Choice: ").strip().upper()
            
            if choice == "P" and task.postpone_count >= 5:
                print(Fore.RED + f"You've postponed this {task.postpone_count} times. That option is no longer available." + Style.RESET_ALL)
                continue
                
            if choice not in ["E", "P", "D", "O"]:
                print("Please enter E, P, D, or O.")
                continue
            break
            
        if choice == "E":
            task.executed_late = True
            task.last_missed_prompt = today_str
            print(Fore.GREEN + "Execution started. Focus up." + Style.RESET_ALL)
        elif choice == "P":
            count = task.postpone_count
            if count == 2:
                print(Fore.YELLOW + "⚠  Heads up: you've postponed this twice already." + Style.RESET_ALL)
            elif count == 3 or count == 4:
                print(Fore.YELLOW + f"""
  ┌─────────────────────────────────────────┐
  │  ⚠  Postponed {count} times.                 │
  │  This task keeps getting pushed back.   │
  │  Is it actually going to happen?        │
  └─────────────────────────────────────────┘""" + Style.RESET_ALL)
            elif count >= 5:
                print(Fore.RED + f"""
  ┌─────────────────────────────────────────┐
  │  ⚠  Postponed {count} times.                 │
  │  This task has never been executed.     │
  │  You have 3 choices:                    │
  └─────────────────────────────────────────┘""" + Style.RESET_ALL)

            print("\nReschedule to:")
            print("[1]  +30 minutes")
            print("[2]  +1 hour")
            print("[3]  +2 hours")
            print("[4]  Tomorrow, same time")
            if count >= 3:
                print("[5]  Custom (type a new deadline)")
                print("[6]  Drop this task instead\n")
            else:
                print("[5]  Custom (type a new deadline)\n")
            
            p_choice = get_valid_input("Choice [1]: ", "1").strip()
            
            if count >= 3 and p_choice == "6":
                task.dropped_at = now.isoformat()
                task.drop_reason = f"user decision — dropped after {count} postpones"
                task.last_missed_prompt = today_str
                print(Fore.WHITE + Style.DIM + f"Dropped after {count} postpones. Good call." + Style.RESET_ALL)
                continue
                
            new_dt = None
            if p_choice == "1":
                new_dt = now + timedelta(minutes=30)
            elif p_choice == "2":
                new_dt = now + timedelta(hours=1)
            elif p_choice == "3":
                new_dt = now + timedelta(hours=2)
            elif p_choice == "4":
                try:
                    orig = datetime.fromisoformat(task.deadline)
                    new_dt = orig + timedelta(days=1)
                except ValueError:
                    new_dt = now + timedelta(days=1)
            elif p_choice == "5":
                custom_input = get_valid_input("New deadline: ")
                parsed = parse_deadline(custom_input)
                if parsed:
                    new_dt = parsed
                else:
                    print("Could not parse date. Skipping postpone.")
            
            if new_dt:
                task.deadline = new_dt.isoformat()
                task.postpone_count += 1
                task.postpone_history.append(now.isoformat())
                task.last_missed_prompt = today_str
                
                # Feature 7: Recalculate reminders when postponed
                calculate_reminder_time(task)
                task.reminder_fired = False
                task.reminder_fired_2 = False
                
                new_count = task.postpone_count
                print(Fore.CYAN + f"Rescheduled to {new_dt.strftime('%A, %d %b at %I:%M %p')}." + Style.RESET_ALL)
                msg = f"Postponed {new_count} time(s) total."
                if new_count >= 2:
                    print(Fore.YELLOW + msg + Style.RESET_ALL)
                else:
                    print(Fore.CYAN + msg + Style.RESET_ALL)
            else:
                print("Invalid choice. Skipping postpone.")
                task.last_missed_prompt = today_str
        elif choice == "D":
            task.dropped_at = now.isoformat()
            task.drop_reason = "user decision — missed deadline"
            task.last_missed_prompt = today_str
            print(Fore.WHITE + Style.DIM + "Task dropped. It's done with." + Style.RESET_ALL)
        elif choice == "O":
            task.offloaded_at = now.isoformat()
            note = get_valid_input("Brief note (who/why) [optional]: ")
            task.offload_note = note
            task.last_missed_prompt = today_str
            print(Fore.WHITE + Style.DIM + "Noted. Responsibility transferred." + Style.RESET_ALL)

    storage.save_tasks(tasks)
    print("")


def command_postpone(task_id: int) -> bool:
    """Direct proactive postpone for any task."""
    tasks = storage.load_tasks()
    task = next((t for t in tasks if t.id == task_id), None)
    
    if not task:
        Messenger.task_not_found(task_id)
        return False
        
    if task.completed or task.dropped_at or task.offloaded_at:
        status = "completed" if task.completed else ("dropped" if task.dropped_at else "offloaded")
        print(f"Task #{task_id} is already {status}. Cannot postpone.")
        return False
        
    if not task.deadline:
        print(f"Task #{task_id} has no deadline set. Add one first: taskflow edit {task_id}")
        return False
        
    count = task.postpone_count
    if count == 2:
        print(Fore.YELLOW + "⚠  Heads up: you've postponed this twice already." + Style.RESET_ALL)
    elif count == 3 or count == 4:
        print(Fore.YELLOW + f"""
  ┌─────────────────────────────────────────┐
  │  ⚠  Postponed {count} times.                 │
  │  This task keeps getting pushed back.   │
  │  Is it actually going to happen?        │
  └─────────────────────────────────────────┘""" + Style.RESET_ALL)
    elif count >= 5:
        print(Fore.RED + f"""
  ┌─────────────────────────────────────────┐
  │  ⚠  Postponed {count} times.                 │
  │  This task has never been executed.     │
  │  You have 3 choices:                    │
  └─────────────────────────────────────────┘""" + Style.RESET_ALL)

    print(f"\nReschedule \"{task.title}\" to:")
    print("[1]  +30 minutes")
    print("[2]  +1 hour")
    print("[3]  +2 hours")
    print("[4]  Tomorrow, same time")
    if count >= 3:
        print("[5]  Custom (type a new deadline)")
        print("[6]  Drop this task instead\n")
    else:
        print("[5]  Custom (type a new deadline)\n")
    
    p_choice = get_valid_input("Choice [1]: ", "1").strip()
    now = datetime.now()
    
    if count >= 3 and p_choice == "6":
        task.dropped_at = now.isoformat()
        task.drop_reason = f"user decision — dropped after {count} postpones"
        storage.save_tasks(tasks)
        print(Fore.WHITE + Style.DIM + f"Dropped after {count} postpones. Good call." + Style.RESET_ALL)
        return True
        
    new_dt = None
    if p_choice == "1":
        new_dt = now + timedelta(minutes=30)
    elif p_choice == "2":
        new_dt = now + timedelta(hours=1)
    elif p_choice == "3":
        new_dt = now + timedelta(hours=2)
    elif p_choice == "4":
        try:
            orig = datetime.fromisoformat(task.deadline)
            new_dt = orig + timedelta(days=1)
        except ValueError:
            new_dt = now + timedelta(days=1)
    elif p_choice == "5":
        custom_input = get_valid_input("New deadline: ")
        parsed = parse_deadline(custom_input)
        if parsed:
            new_dt = parsed
        else:
            print("Could not parse date. Skipping postpone.")
    
    if new_dt:
        task.deadline = new_dt.isoformat()
        task.postpone_count += 1
        task.postpone_history.append(now.isoformat())
        
        calculate_reminder_time(task)
        task.reminder_fired = False
        task.reminder_fired_2 = False
        
        storage.save_tasks(tasks)
        
        new_count = task.postpone_count
        print(Fore.CYAN + f"Rescheduled to {new_dt.strftime('%A, %d %b at %I:%M %p')}." + Style.RESET_ALL)
        msg = f"Postponed {new_count} time(s) total."
        if new_count >= 2:
            print(Fore.YELLOW + msg + Style.RESET_ALL)
        else:
            print(Fore.CYAN + msg + Style.RESET_ALL)
        return True
    else:
        print("Invalid choice. Skipping postpone.")
        return False



def calculate_reminder_time(task) -> Optional[datetime]:
    """Calculate the ideal reminder time for a task based on rules."""
    if not task.deadline:
        return None
        
    try:
        dt = datetime.fromisoformat(task.deadline)
    except ValueError:
        return None
        
    p_lower = (task.priority or "medium").lower()
    d_type = getattr(task, 'deadline_type', None)
    
    r1 = None
    r2 = None
    
    if d_type == "hard":
        if p_lower in ["high", "critical"]:
            r1 = dt - timedelta(hours=2)
            r2 = dt - timedelta(minutes=30)
        elif p_lower in ["medium", "strategic"]:
            r1 = dt - timedelta(hours=1)
            r2 = dt - timedelta(minutes=20)
        elif p_lower in ["low", "noise", "purge"]:
            r1 = dt - timedelta(minutes=30)
    else:
        # Soft deadline rules
        if p_lower in ["high", "critical"]:
            r1 = dt - timedelta(hours=1)
        elif p_lower in ["medium", "strategic"]:
            r1 = dt - timedelta(minutes=30)
        elif p_lower in ["low", "noise", "purge"]:
            r1 = dt - timedelta(minutes=15)
            
    now = datetime.now()
    if r1 and r1 < now:
        # Rule 8: If already past, set to 5 mins from now
        r1 = now + timedelta(minutes=5)
        r2 = None # Drop second reminder if first is already crunched
        print("Note: reminder time already passed. Set to fire in 5 minutes.")
        
    task.reminder_time = r1.isoformat() if r1 else None
    task.reminder_time_2 = r2.isoformat() if r2 else None
    return r1


def check_reminders(tasks: List[Task]) -> List[Task]:
    """Check for due reminders on startup."""
    due = []
    now = datetime.now()
    
    for task in tasks:
        if task.completed or task.dropped_at or task.offloaded_at:
            continue
        if task.reminder_fired and task.reminder_dismissed:
            continue
        if not task.reminder_time:
            continue
            
        is_due = False
        try:
            r1 = datetime.fromisoformat(task.reminder_time)
            if now >= r1 and not task.reminder_fired:
                is_due = True
                task.reminder_fired = True
        except ValueError:
            pass
            
        if not is_due and task.reminder_time_2:
            try:
                r2 = datetime.fromisoformat(task.reminder_time_2)
                if now >= r2 and not task.reminder_fired_2:
                    is_due = True
                    task.reminder_fired_2 = True
            except ValueError:
                pass
                
        if is_due:
            due.append(task)
            
    if due:
        storage.save_tasks(tasks)
        if len(due) >= 3:
            print(Fore.YELLOW + f"You have {len(due)} reminders firing at once. Showing one at a time." + Style.RESET_ALL)
            
        for task in due:
            try:
                dt = datetime.fromisoformat(task.deadline)
                now = datetime.now()
                today = now.replace(hour=0, minute=0, second=0, microsecond=0)
                task_date = dt.replace(hour=0, minute=0, second=0, microsecond=0)
                
                if dt < now:
                    diff = int((now - dt).total_seconds() / 60)
                    due_str = f"OVERDUE by {diff} min"
                    due_line = f"{Fore.RED}{due_str}{Style.RESET_ALL}"
                else:
                    diff = int((dt - now).total_seconds() / 60)
                    if task_date == today:
                        time_formatted = dt.strftime('%I:%M %p').lstrip('0')
                        due_str = f"Today at {time_formatted}  (in {diff} min)"
                    elif task_date == today + timedelta(days=1):
                        time_formatted = dt.strftime('%I:%M %p').lstrip('0')
                        due_str = f"Tomorrow at {time_formatted}  (in {diff} min)"
                    else:
                        date_formatted = dt.strftime('%a %d %b')
                        time_formatted = dt.strftime('%I:%M %p').lstrip('0')
                        due_str = f"{date_formatted}, {time_formatted}  (in {diff} min)"
                    due_line = due_str
            except ValueError:
                due_line = str(task.deadline)

            hard_line = ""
            if getattr(task, 'deadline_type', None) == "hard":
                hard_line = f"\n  ║  Deadline: {Fore.RED}HARD{Fore.CYAN}{' ' * 29}║"
                
            print(Fore.CYAN + f"""
  ╔══════════════════════════════════════════════╗
  ║  🔔  REMINDER                               ║
  ║  Task:     {task.title[:30]:<30}║
  ║  Due:      {due_line:<30}║
  ║  Priority: {task.priority:<6}  ·  Duration: {str(task.duration or 'None'):<12}║{hard_line}
  ╚══════════════════════════════════════════════╝""" + Style.RESET_ALL)
            
            print("\n  [Enter] Noted  ·  [D] Dismiss forever  ·  [S] Start focus now\n")
            choice = get_valid_input("Choice: ", "").strip().upper()
            
            if choice == "D":
                task.reminder_dismissed = True
                print(Fore.WHITE + Style.DIM + "Reminder dismissed. Won't show again." + Style.RESET_ALL)
                storage.save_tasks(tasks)
            elif choice == "S":
                print(f"Focus session: taskflow focus --id {task.id}")
            else:
                print(Fore.CYAN + Style.DIM + "Reminder noted." + Style.RESET_ALL)
                
    return due


def command_remind(task_id: int, set_str: str = None, clear: bool = False) -> bool:
    """Handle the remind command."""
    tasks = storage.load_tasks()
    task = next((t for t in tasks if t.id == task_id), None)
    
    if not task:
        Messenger.task_not_found(task_id)
        return False
        
    if clear:
        task.reminder_time = None
        task.reminder_time_2 = None
        task.reminder_fired = False
        task.reminder_fired_2 = False
        task.reminder_dismissed = False
        storage.save_tasks(tasks)
        print(f"Reminders cleared for task #{task_id}.")
        return True
        
    if set_str:
        parsed = parse_deadline(set_str)
        if not parsed:
            print("Could not understand that date.")
            return False
        task.reminder_time = parsed.isoformat()
        task.reminder_fired = False
        task.reminder_dismissed = False
        storage.save_tasks(tasks)
        print(f"Reminder updated: {parsed.strftime('%A %d %b at %I:%M %p')}")
        return True
        
    # Show current
    print(f"Task #{task.id} · {task.title}")
    
    def fmt_rem(rt_str, fired):
        if not rt_str:
            return None
        try:
            dt = datetime.fromisoformat(rt_str)
            status = "[fired]" if fired else "[pending]"
            return f"{dt.strftime('%A %d %b at %I:%M %p')}  {status}"
        except Exception:
            return str(rt_str)
            
    r1 = fmt_rem(task.reminder_time, task.reminder_fired)
    r2 = fmt_rem(task.reminder_time_2, task.reminder_fired_2)
    
    if not r1 and not r2:
        print("No reminders set.")
    else:
        if r1:
            print(f"Reminder 1: {r1}")
        if r2:
            print(f"Reminder 2: {r2}")
            
    if task.deadline:
        hard_str = "[HARD]" if getattr(task, 'deadline_type', None) == "hard" else "[SOFT]"
        try:
            ddt = datetime.fromisoformat(task.deadline)
            print(f"Deadline:   {ddt.strftime('%A %d %b at %I:%M %p')}  {hard_str}")
        except Exception:
            print(f"Deadline:   {task.deadline}  {hard_str}")
            
    return True







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


# ============================================================================
# FOCUS MANAGER CLASS - Add this after imports but before existing functions
# ============================================================================

class FocusManager:
    """Manages focus sessions with distraction blocking."""
    
    def __init__(self):
        self.blocker = None
        self.focus_mode = "gentle"  # gentle, strict, or none
        self.active_focus_task = None
        self.blocked_at_start = None
        self.focus_start_time = None
        
    def init_blocker(self, mode="gentle"):
        """Initialize the appropriate blocker."""
        self.focus_mode = mode
        
        try:
            from .system_detector import SystemDetector
            
            if mode == "strict":
                if SystemDetector.get_os() == "windows" and not SystemDetector.is_admin():
                    print("\n❌ ACCESS DENIED: Strict blocking requires Administrator privileges.")
                    print("   To fix this:")
                    print("   1. Close this terminal")
                    print("   2. Right-click Command Prompt (or PowerShell)")
                    print("   3. Select 'Run as administrator'")
                    print("   4. Run the focus command again")
                    return False
                
                self.blocker = SystemDetector.get_distraction_blocker(force_gentle=False)
            else:
                self.blocker = SystemDetector.get_distraction_blocker(force_gentle=True)
            
            return True
        except Exception as e:
            print(f"⚠️  Could not initialize blocker: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start_focus_session(self, task_id: int, task_title: str, task_notes: str = "", 
                            priority: str = "medium", minutes: int = 25, 
                           sites=None, apps=None, mode="gentle"):
        """Start a focus session with optional blocking."""
        
        # Initialize blocker
        if not self.init_blocker(mode):
            print("⚠️  Starting focus without blocking features.")
            mode = "none"
        
        # Record what we're blocking
        self.blocked_at_start = {
            "sites": sites or [],
            "apps": apps or []
        }
        self.active_focus_task = task_id
        self.focus_start_time = datetime.now()
        
        # Start focus timer (sync state to disk)
        if not time_tracker.start_focus(task_id, task_title, task_notes, 
                                        priority, minutes, sites, mode):
            return False
        
        # Start blocking if requested
        if self.blocker and (sites or apps):
            print(f"\n🎯 Starting Focus Mode: {mode.upper()}")
            print(f"   Task: {task_title}")
            print(f"   Duration: {minutes} minutes")
            
            if sites:
                print(f"   Avoiding websites: {', '.join(sites[:3])}")
                if len(sites) > 3:
                    print(f"   ... and {len(sites) - 3} more")
            
            if apps:
                print(f"   Avoiding apps: {', '.join(apps[:3])}")
                if len(apps) > 3:
                    print(f"   ... and {len(apps) - 3} more")
            
            # Actually block
            gentle_mode = (mode == "gentle")
            self.blocker.start_focus(sites, apps, gentle_mode=gentle_mode)
            
            if mode == "strict" and not SystemDetector.is_admin():
                print("\n⚠️  Note: For strict blocking, run TaskFlow as Administrator")
                print("   Currently running in gentle reminder mode")
        
        return True
    

    def end_focus_session(self):
        """End the current focus session and restore everything."""
        
        # End focus timer first
        success = time_tracker.end_focus()
        
        # End blocking - IMPORTANT: Always call end_focus on blocker
        if self.blocker:
            # Check if blocker has end_focus method
            if hasattr(self.blocker, 'end_focus'):
                self.blocker.end_focus()
            else:
                # Fallback: manually unblock
                if hasattr(self.blocker, 'unblock_websites'):
                    self.blocker.unblock_websites()
                if hasattr(self.blocker, 'unblock_applications'):
                    self.blocker.unblock_applications()
                # Mark as inactive
                self.blocker.is_active = False
        
        # Clear state
        self.active_focus_task = None
        self.blocked_at_start = None
        
        # Show summary
        if success and self.focus_start_time:
            duration = datetime.now() - self.focus_start_time
            minutes = int(duration.total_seconds() / 60)
            print(f"\n✅ Focus session completed: {minutes} minutes of focused work!")
        
        self.focus_start_time = None
        return success
    
    def get_focus_status(self):
        """Get detailed focus status including blocking."""
        focus_status = time_tracker.check_focus()
        
        if not focus_status:
            return {
                "focus_active": False,
                "blocking_active": False,
                "message": "No active focus session"
            }
        
        result = {
            "focus_active": True,
            "task_id": focus_status.get("task_id"),
            "task_title": focus_status.get("task_title"),
            "task_notes": focus_status.get("task_notes"),
            "priority": focus_status.get("priority"),
            "minutes_left": focus_status.get("remaining_minutes"), # Consistent with check_focus return
            "remaining_seconds": focus_status.get("remaining_seconds"),
            "paused": focus_status.get("paused", False),
            "cycles_completed": focus_status.get("cycles_completed", 0),
            "blocking_active": False,
            "blocking_mode": None,
            "blocked_items": {}
        }
        
        # Add blocking info if available
        if self.blocker and self.blocker.is_active:
            block_status = self.blocker.get_status()
            result.update({
                "blocking_active": True,
                "blocking_mode": "strict" if not block_status.get("gentle_mode") else "gentle",
                "blocked_items": {
                    "sites": block_status.get("blocked_sites", []),
                    "apps": block_status.get("blocked_apps", [])
                },
                "blocked_since": block_status.get("since")
            })
        elif focus_status.get("blocked_sites"):
            # Fallback for Inter-Process Sync (e.g. Server reading CLI session)
            result.update({
                "blocking_active": True,
                "blocking_mode": focus_status.get("mode", "gentle"),
                "blocked_items": {
                    "sites": focus_status.get("blocked_sites", []),
                    "apps": []
                }
            })
        
        return result
    
    def is_focus_active(self):
        """Check if any focus session is active."""
        return time_tracker.check_focus() is not None

focus_manager = FocusManager()


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
        self.on_session_expired = None
        self._load_state()
    
    def _load_state(self, quiet: bool = False):
        """Load saved focus state from disk."""
        try:
            from task_manager.storage import storage
            state_file = storage.data_dir / "focus_state.json"
            if state_file.exists():
                state = None
                for _ in range(10): # Retry up to 1 second
                    try:
                        with open(state_file, 'r') as f:
                            state = json.load(f)
                        break
                    except PermissionError:
                        time.sleep(0.1)
                        
                if state and state.get('active_session'):
                    start_time_str = state['active_session']['start_time']
                    start_time = datetime.fromisoformat(start_time_str)
                    minutes = state['active_session']['minutes']
                    
                    # Handle pausing logic for elapsed time
                    is_paused = state['active_session'].get('paused', False)
                    if is_paused:
                        paused_at = datetime.fromisoformat(state['active_session']['paused_at'])
                        elapsed = (paused_at - start_time).total_seconds()
                    else:
                        elapsed = (datetime.now() - start_time).total_seconds()
                    
                    remaining = (minutes * 60) - elapsed
                    
                    if remaining > 0:
                        self.active_session = state['active_session']
                        self.start_time = time.time() - elapsed
                    else:
                        if not quiet:
                            print(f"⏰ Previous focus session expired.")
                        
                        # Increment cycle since it completed naturally while CLI was closed
                        self.increment_cycle()
                        
                        self._save_state({'active_session': None, 'start_time': None})
                        if hasattr(self, 'on_session_expired') and self.on_session_expired:
                            self.on_session_expired()
                else:
                    self.active_session = None
                    self.start_time = None
        except (json.JSONDecodeError, FileNotFoundError, KeyError, ValueError, PermissionError) as e:
            self.active_session = None
            self.start_time = None

    
    def _save_state(self, state=None):
        """Save focus state to disk."""
        try:
            from task_manager.storage import storage
            state_file = storage.data_dir / "focus_state.json"
            state_file.parent.mkdir(parents=True, exist_ok=True)
            
            if state is None:
                state = {
                    'active_session': self.active_session,
                    'start_time': self.start_time,
                    'saved_at': datetime.now().isoformat()
                }
            
            for _ in range(10): # Retry up to 1 second
                try:
                    with open(state_file, 'w') as f:
                        json.dump(state, f)
                    break
                except PermissionError:
                    time.sleep(0.1)
        except Exception:
            pass
            
    def get_cycles(self):
        try:
            from task_manager.storage import storage
            stats_file = storage.data_dir / "user_stats.json"
            if stats_file.exists():
                with open(stats_file, 'r') as f:
                    stats = json.load(f)
                    today = datetime.now().strftime('%Y-%m-%d')
                    if stats.get('last_completion_date') == today:
                        return stats.get('daily_completions', 0)
        except:
            pass
        return 0
        
    def increment_cycle(self):
        # We now use the unified _generate_dopamine for tracking
        dopa = _generate_dopamine()
        return dopa
    
    def start_focus(self, task_id: int, task_title: str, task_notes: str = "", 
                    priority: str = "medium", minutes: int = 25, 
                    blocked_sites: list = None, mode: str = "gentle"):
        """Start a focus session for a task."""
        self.active_session = {
            'task_id': task_id,
            'task_title': task_title,
            'task_notes': task_notes,
            'priority': priority,
            'minutes': minutes,
            'blocked_sites': blocked_sites or [],
            'mode': mode,
            'start_time': datetime.now().isoformat(),
            'paused': False
        }
        self.start_time = time.time()
        self._save_state()
        Messenger.focus_start(task_title, minutes)
        return self.active_session

    def pause_focus(self):
        """Pause current session."""
        self._load_state(quiet=True)
        if self.active_session and not self.active_session.get('paused'):
            self.active_session['paused'] = True
            self.active_session['paused_at'] = datetime.now().isoformat()
            self._save_state()

    def resume_focus(self):
        """Resume current session."""
        self._load_state(quiet=True)
        if self.active_session and self.active_session.get('paused'):
            paused_at = datetime.fromisoformat(self.active_session['paused_at'])
            start_time = datetime.fromisoformat(self.active_session['start_time'])
            
            pause_duration = datetime.now() - paused_at
            # Shift start time forward so time doesn't appear to have elapsed
            new_start_time = start_time + pause_duration
            
            self.active_session['start_time'] = new_start_time.isoformat()
            self.active_session['paused'] = False
            del self.active_session['paused_at']
            
            self.start_time += pause_duration.total_seconds()
            self._save_state()
    
    def check_focus(self):
        """Check current focus session status."""
        self._load_state(quiet=True)
        
        if not self.active_session:
            return None
            
        start_time = datetime.fromisoformat(self.active_session['start_time'])
        is_paused = self.active_session.get('paused', False)
        
        if is_paused:
            paused_at = datetime.fromisoformat(self.active_session['paused_at'])
            elapsed = (paused_at - start_time).total_seconds()
        else:
            elapsed = (datetime.now() - start_time).total_seconds()
            
        remaining = (self.active_session['minutes'] * 60) - elapsed
        
        if remaining <= 0:
            session = self.active_session.copy()
            if hasattr(self, 'on_session_expired') and self.on_session_expired:
                self.on_session_expired()
            else:
                self.increment_cycle()
                self._save_state({'active_session': None, 'start_time': None})
                self.active_session = None
                self.start_time = None
            return {'status': 'completed', 'session': session, 'cycles_completed': self.get_cycles()}

        return {
            'status': 'active',
            'task_id': self.active_session.get('task_id'),
            'task_title': self.active_session.get('task_title'),
            'task_notes': self.active_session.get('task_notes'),
            'priority': self.active_session.get('priority'),
            'blocked_sites': self.active_session.get('blocked_sites', []),
            'mode': self.active_session.get('mode', 'gentle'),
            'elapsed_minutes': int(elapsed / 60),
            'remaining_minutes': int(remaining / 60),
            'remaining_seconds': int(remaining % 60),
            'paused': is_paused,
            'cycles_completed': self.get_cycles()
        }
    
    def end_focus(self, completed: bool = False):
        """End current focus session."""
        if not self.active_session:
            Messenger.note("No active focus session to end.")
            return
        
        session_minutes = self.active_session.get('minutes', 25)
        task_title = self.active_session.get('task_title', 'Task')
        try:
            from task_manager.storage import storage
            tasks = storage.load_tasks()
            
            for task in tasks:
                if task.id == self.active_session.get('task_id'):
                    task.add_focus_minutes(session_minutes)
                    storage.save_tasks(tasks)
                    break
        except Exception:
            pass
            
        if completed:
            self.increment_cycle()
        
        Messenger.focus_complete(task_title, session_minutes)
        self.active_session = None
        self.start_time = None
        self._save_state({'active_session': None, 'start_time': None})
        print("🧹 Focus session cleared from memory.")


# Global instance
time_tracker = TimeTracker()
time_tracker.on_session_expired = focus_manager.end_focus_session

if not time_tracker.active_session:
    if focus_manager.blocker and focus_manager.blocker.is_active:
        focus_manager.end_focus_session()



# =========================================================
# INTELLIGENT MOMENTUM ENGINE
# =========================================================
def get_momentum_targets(limit=3):
    """Priority selection engine to find optimal next tasks."""
    from datetime import datetime
    from task_manager import storage
    
    tasks = storage.load_tasks()
    timeline = storage.load_timeline()
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # 1. Timeline TODAY targets
    today_task_ids = {int(tid) for tid, tslot in timeline.items() if tslot.startswith(today_str)}
    today_tasks = [t for t in tasks if not t.completed and t.id in today_task_ids]
    
    # 2. HIGH priority incomplete targets (Critical, Strategic, High)
    high_impact = [t for t in tasks if not t.completed and t.id not in today_task_ids and t.priority in ['Critical', 'Strategic']]
    high_priority = [t for t in tasks if not t.completed and t.id not in today_task_ids and t.priority == 'High']
    
    # 3. Remaining unscheduled incomplete targets
    other_tasks = [t for t in tasks if not t.completed and t.id not in today_task_ids and t.priority not in ['Critical', 'Strategic', 'High']]
    
    # Combine pools in order and deduplicate logically
    momentum_pool = today_tasks + high_impact + high_priority + other_tasks
    
    targets = []
    seen_ids = set()
    for t in momentum_pool:
        if t.id not in seen_ids:
            targets.append({
                "id": t.id,
                "title": t.title,
                "priority": t.priority,
                "tags": t.tags,
                "notes": t.notes
            })
            seen_ids.add(t.id)
            if len(targets) >= limit:
                break
                
    return targets

def complete_focus(efficiency_score=0, time_saved=0, time_used=0):
    """Early Completion Success Flow: End session, log stats, trigger momentum mode."""
    status = focus_manager.get_focus_status()
    if not status or not status.get("focus_active"):
        return False
        
    task_title = status.get("task_title", "Task")
    
    print(f"\n[FOCUS COMPLETE] ✦ MISSION SUCCESS ✦")
    print(f"Task: {task_title}")
    if time_used > 0:
        print(f"Time Used: {time_used}m")
    if time_saved > 0:
        print(f"Saved: {time_saved}m")
    if efficiency_score > 0:
        print(f"Efficiency: {efficiency_score}%")
    print("[MOMENTUM MODE] Ready for next sequence.")
    
    # Force end the session properly globally
    time_tracker.end_focus(completed=True)
    focus_manager.end_focus_session()
    
    return True


# =========================================================
# CORE TASK OPERATIONS (Enhanced) - MAIN.PY IMPORTS THESE
# =========================================================

def add_task(is_hard: bool = False, preset_deadline: str = None, preset_duration: str = None, preset_priority: str = None) -> bool:
    """Add a new task with improved UX."""
    tasks = storage.load_tasks()
    manager = TaskManager(tasks)
    
    title = get_valid_input("Task title: ")
    title = validate_title(title)
    if not title:
        return False
    
    if preset_priority:
        priority_input = preset_priority
    else:
        priority_input = get_valid_input("Priority (Low/Medium/High) [Medium]: ", "Medium")
        
    try:
        priority = normalize_priority(priority_input)
    except NameError:
        priority = priority_input.capitalize()
    
    # Ask for tags
    tags_input = get_valid_input("Tags (comma-separated, optional): ")
    tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
    
    # Ask for duration
    duration = None
    if preset_duration:
        duration = preset_duration.lower()
    else:
        while True:
            dur_input = get_valid_input("Duration (15m/30m/1h/2h/3h/4h+) [skip]: ")
            if not dur_input:
                break
            dur_input = dur_input.lower()
            if dur_input in ["15m", "30m", "1h", "2h", "3h", "4h+"]:
                duration = dur_input
                break
            else:
                print("Invalid duration. Choose from: 15m, 30m, 1h, 2h, 3h, 4h+")
                dur_input = get_valid_input("Duration (15m/30m/1h/2h/3h/4h+) [skip]: ")
                if not dur_input:
                    break
                dur_input = dur_input.lower()
                if dur_input in ["15m", "30m", "1h", "2h", "3h", "4h+"]:
                    duration = dur_input
                break

    # Ask for deadline
    deadline_iso = None
    deadline_type = "hard" if is_hard else None
    
    if preset_deadline:
        parsed_dl = parse_deadline(preset_deadline)
        if parsed_dl:
            deadline_iso = parsed_dl.isoformat()
            if not is_hard:
                deadline_type = "soft"
        else:
            print("Could not understand preset deadline.")
            
    if not deadline_iso:
        while True:
            dl_input = get_valid_input("Deadline (e.g. tomorrow 3pm, Friday, in 2h): ")
            if not dl_input:
                break
            parsed_dl = parse_deadline(dl_input)
            if parsed_dl:
                print(f"→ Deadline set: {parsed_dl.strftime('%A, %d %b %Y at %H:%M')}")
                confirm = get_valid_input("Confirm? [Y/n]: ", "y").lower()
                if confirm == "y" or confirm == "":
                    deadline_iso = parsed_dl.isoformat()
                    break
                else:
                    dl_input2 = get_valid_input("Deadline (e.g. tomorrow 3pm, Friday, in 2h): ")
                    if not dl_input2:
                        break
                    parsed_dl2 = parse_deadline(dl_input2)
                    if parsed_dl2:
                        print(f"→ Deadline set: {parsed_dl2.strftime('%A, %d %b %Y at %H:%M')}")
                        confirm2 = get_valid_input("Confirm? [Y/n]: ", "y").lower()
                        if confirm2 == "y" or confirm2 == "":
                            deadline_iso = parsed_dl2.isoformat()
                    break
            else:
                print("Could not understand that date. Try: 'tomorrow 3pm', 'Friday', 'in 2 hours'")
                dl_input2 = get_valid_input("Deadline (e.g. tomorrow 3pm, Friday, in 2h): ")
                if not dl_input2:
                    break
                parsed_dl2 = parse_deadline(dl_input2)
                if parsed_dl2:
                    print(f"→ Deadline set: {parsed_dl2.strftime('%A, %d %b %Y at %H:%M')}")
                    confirm2 = get_valid_input("Confirm? [Y/n]: ", "y").lower()
                    if confirm2 == "y" or confirm2 == "":
                        deadline_iso = parsed_dl2.isoformat()
                break
                
        # Ask for deadline type
        if deadline_iso and not is_hard and not preset_deadline:
            print("\nDeadline type:")
            print("[1] Soft — flexible, gentle reminder (default)")
            print("[2] Hard — critical, strong alert if missed")
            dt_input = get_valid_input("Choice [1]: ", "1").strip()
            if dt_input == "2":
                deadline_type = "hard"
            else:
                deadline_type = "soft"
        elif deadline_iso and is_hard:
            deadline_type = "hard"

    task = Task(
        id=0,  # Will be auto-assigned
        title=title,
        priority=priority,
        tags=tags
    )
    task.duration = duration
    task.deadline = deadline_iso
    task.deadline_type = deadline_type
    
    if deadline_iso:
        calculate_reminder_time(task)
        
    try:
        task_id = manager.add_task(task)
        storage.save_tasks(manager.tasks)
        if duration:
            Messenger.success(f"Task #{task_id} added. · {duration} estimated.")
        else:
            Messenger.success(f"Task #{task_id} added successfully.")
        return True
    except Exception as e:
        Messenger.careful(f"Could not add task: {e}")
        return False

def dump_task(title: str) -> dict:
    """Frictionless capture: instantly add a task without prompts."""
    import re
    tasks = storage.load_tasks()
    manager = TaskManager(tasks)
    
    # Frictionless Parser: Extract #tags and !priority
    tags = ["inbox"]
    priority = "Medium"
    
    # Extract tags starting with #
    extracted_tags = re.findall(r'#(\w+)', title)
    for t in extracted_tags:
        if t.lower() not in [tg.lower() for tg in tags]:
            tags.append(t)
    
    # Extract priority starting with !
    # Using (?!\w) ensures we don't match "!hello" as "!h"
    extracted_priorities = re.findall(r'!(low|medium|high|noise|strategic|critical|l|m|h|p|purge)(?!\w)', title, re.IGNORECASE)
    if extracted_priorities:
        priority = extracted_priorities[-1] # Take the last one specified
        
    # Clean the title by removing the extracted markers
    clean_title = re.sub(r'#\w+', '', title)
    clean_title = re.sub(r'!(low|medium|high|noise|strategic|critical|l|m|h|p|purge)(?!\w)', '', clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r'\s+', ' ', clean_title).strip()  # Collapse residual whitespace
    clean_title = validate_title(clean_title)
    
    if not clean_title:
        return None
        
    task = Task(
        id=0,
        title=clean_title,
        priority=normalize_priority(priority.capitalize()),
        tags=tags
    )
    
    try:
        task_id = manager.add_task(task)
        storage.save_tasks(manager.tasks)
        try:
            prin_tags = ", ".join(f"#{t}" for t in tags)
            print(f"\nCaptured: {clean_title} | [{task.priority}] {prin_tags}")
        except Exception:
            pass # Ignore print errors in background daemon
        return task.to_dict()
    except Exception as e:
        try:
            print(f"Capture failed: {e}")
        except Exception:
            pass
        return None

def kill_web_ui():
    """Find and terminate any existing Web UI server processes on port 18083."""
    import subprocess
    import sys
    import os
    import signal
    import time
    import socket

    port = 18083
    print(f"📡 Scanning for Mission Control processes on port {port}...")
    
    try:
        if sys.platform == "win32":
            # Windows: Find ALL PIDs on port (not just LISTENING — catches stale too)
            cmd = f'netstat -ano | findstr :{port}'
            try:
                output = subprocess.check_output(cmd, shell=True).decode()
            except subprocess.CalledProcessError:
                output = ""
            
            pids = set()
            for line in output.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        pid = parts[4].strip()
                        if pid.isdigit() and int(pid) > 0:
                            pids.add(pid)
                    except (ValueError, IndexError):
                        pass
            
            if not pids:
                print("✅ No active server processes found.")
                return True

            for pid in pids:
                print(f"🛑 Terminating PID {pid}...")
                subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
            
        else:
            # Unix/Mac: Find PID using lsof
            try:
                cmd = f'lsof -ti:{port}'
                pid_output = subprocess.check_output(cmd, shell=True).decode().strip()
                pids = [p.strip() for p in pid_output.split('\n') if p.strip().isdigit()]
                if pids:
                    for pid in pids:
                        print(f"🛑 Terminating PID {pid}...")
                        os.kill(int(pid), signal.SIGKILL)
                else:
                    print("✅ No active server processes found.")
                    return True
            except subprocess.CalledProcessError:
                print("✅ No active server processes found.")
                return True

        # Wait up to 3s for port to be released
        for _ in range(6):
            time.sleep(0.5)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            is_taken = sock.connect_ex(('127.0.0.1', port)) == 0
            sock.close()
            if not is_taken:
                break

        print("✨ Mission Control cleared.")
        return True
    except Exception as e:
        print(f"⚠️  Error during cleanup: {e}")

def open_web_ui(force=False):
    """Launch the System Control Web Dashboard (Quantum Resolve)."""
    import subprocess
    import time
    import webbrowser
    import socket
    import sys
    from pathlib import Path

    port = 18083
    url = f"http://127.0.0.1:{port}"
    
    if force:
        kill_web_ui()
        time.sleep(0.5) # Brief cooldown for port release
    else:
        # Check if port is taken
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        is_taken = sock.connect_ex(('127.0.0.1', port)) == 0
        sock.close()
        
        if is_taken:
            print(f"📡 Mission Control already active at {url}")
            print("   (Use 'taskflow ui --restart' to force a fresh session)")
            webbrowser.open(url)
            return

    print("🚀 Initializing Quantum Resolve HUD...")
    # Get server path
    server_path = Path(__file__).parent / "server.py"
    
    try:
        # Launch server as detached background process
        if sys.platform == "win32":
            subprocess.Popen([sys.executable, str(server_path)], 
                             creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen([sys.executable, str(server_path)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        
        # Success delay
        time.sleep(1.5)
        webbrowser.open(url)
        print(f"✅ Mission Dashboard live at {url}")
    except Exception as e:
        print(f"❌ Failed to reach Mission Control: {e}")


def format_time_remaining(td: timedelta) -> str:
    """Format timedelta for pressure warnings."""
    if td.total_seconds() < 0:
        total = abs(td.total_seconds())
        if total > 3600:
            h = int(total // 3600)
            m = int((total % 3600) // 60)
            return f"OVERDUE {h}h {m}m"
        else:
            m = int(total // 60)
            return f"OVERDUE {m}m"
            
    secs = td.total_seconds()
    if secs > 3600:
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        return f"{h}h {m}m left"
    elif secs >= 60:
        m = int(secs // 60)
        return f"{m}m left"
    else:
        return f"{int(secs)}s left"


def get_pressure_level(task) -> int:
    """Calculate the pressure level based on deadline proximity."""
    if task.completed or not task.deadline:
        return 0
        
    try:
        dt = datetime.fromisoformat(task.deadline)
    except ValueError:
        return 0
        
    td = dt - datetime.now()
    secs = td.total_seconds()
    
    if secs < 0:
        return 3 # Overdue
    elif secs < 15 * 60: # 15 mins
        return 3 # Critical
    elif secs <= 3600: # 1 hour
        return 2 # Near
    elif secs <= 3 * 3600: # 3 hours
        return 1 # Approaching
    else:
        return 0 # No pressure


def list_tasks(filter_status: Optional[str] = None, 
               filter_priority: Optional[str] = None,
               filter_tag: Optional[str] = None,
               show_all: bool = False,
               sort_by: Optional[str] = None) -> None:
    """List tasks with advanced filtering."""
    handle_missed_tasks()
    
    tasks = storage.load_tasks()
    
    if not tasks:
        Messenger.empty_list()
        return
        
    # Apply filters
    filtered_tasks = []
    for task in tasks:
        if not show_all and (task.dropped_at or task.offloaded_at):
            continue
            
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

    # Apply sorting if requested
    if sort_by == "priority":
        priority_order = {"high": 0, "medium": 1, "low": 2}
        filtered_tasks.sort(
            key=lambda t: priority_order.get(
                (t.priority or "").lower(), 1
            )
        )

    elif sort_by == "created":
        filtered_tasks.sort(
            key=lambda t: t.created_at or ""
        )

    elif sort_by == "due":
        filtered_tasks.sort(
            key=lambda t: t.deadline or "9999-12-31"
        )

    if sort_by:
        Messenger.note(f"Sorted by {sort_by}.")

    if not filtered_tasks:
        if filter_status == "done":
            Messenger.note("You haven't completed any tasks yet.")
        elif filter_status == "todo":
            Messenger.no_pending_tasks()
        else:
            Messenger.note("No tasks match your filters.")
        return
    
    shown = 0
    print()
    for task in filtered_tasks:
        if not show_all and shown >= MAX_VISIBLE_TASKS:
            Messenger.note(f"Showing first {MAX_VISIBLE_TASKS} tasks. Use '--all' to view everything.")
            break
        
        title_color = Fore.WHITE + Style.BRIGHT
        pressure_suffix = ""
        hard_pressure_line = ""
        
        if not task.completed and not task.dropped_at and not task.offloaded_at:
            pressure = get_pressure_level(task)
            if pressure > 0 and task.deadline:
                try:
                    dt = datetime.fromisoformat(task.deadline)
                    td = dt - datetime.now()
                    rem_str = format_time_remaining(td)
                    
                    if pressure == 3:
                        if getattr(task, 'deadline_type', None) == "hard":
                            title_color = Fore.RED + Style.BRIGHT
                            hard_pressure_line = f"\n      → {Fore.RED}Hard deadline. Execute or reschedule now.{Style.RESET_ALL}"
                        else:
                            title_color = Fore.YELLOW + Style.BRIGHT
                        if td.total_seconds() < 0:
                            pressure_suffix = f" · {Fore.RED + Style.BRIGHT}{rem_str}{Style.RESET_ALL}"
                        else:
                            pressure_suffix = f" · {Fore.RED + Style.BRIGHT}{rem_str} ⚠{Style.RESET_ALL}"
                    elif pressure == 2:
                        title_color = Fore.YELLOW
                        pressure_suffix = f" · {Fore.YELLOW + Style.BRIGHT}{rem_str}{Style.RESET_ALL}"
                        if getattr(task, 'deadline_type', None) == "hard":
                            hard_pressure_line = f"\n      → {Fore.RED}Hard deadline. Execute or reschedule now.{Style.RESET_ALL}"
                    elif pressure == 1:
                        pressure_suffix = f" · {Fore.YELLOW}{rem_str}{Style.RESET_ALL}"
                except ValueError:
                    pass
                    
        if task.completed or task.dropped_at or task.offloaded_at:
            title_color = Style.DIM
            
        postpone_suffix = ""
        if task.postpone_count >= 5:
            postpone_suffix = f"  {Fore.RED}(postponed ×{task.postpone_count}) ⚠⚠{Style.RESET_ALL}"
        elif task.postpone_count >= 3:
            postpone_suffix = f"  {Fore.YELLOW}(postponed ×{task.postpone_count}) ⚠{Style.RESET_ALL}"
        elif task.postpone_count == 2:
            postpone_suffix = f"  {Fore.YELLOW}(postponed ×2){Style.RESET_ALL}"
            
        duration_str = f"  {Style.DIM}[{task.duration}]{Style.RESET_ALL}" if task.duration else ""
        
        # Priority colors
        p_lower = (task.priority or "").lower()
        if p_lower in ["critical", "high"]:
            p_color = Fore.RED
        elif p_lower in ["strategic", "medium"]:
            p_color = Fore.CYAN
        elif p_lower in ["noise", "low", "purge"]:
            p_color = Fore.WHITE + Style.DIM
        else:
            p_color = Fore.WHITE
            
        priority_str = f" · {p_color}{task.priority}{Style.RESET_ALL}"
        
        # Tags colors
        if task.tags:
            formatted_tags = ", #".join(task.tags)
            tags_str = f" · {Fore.BLUE}#{formatted_tags}{Style.RESET_ALL}"
        else:
            tags_str = ""
        
        deadline_str = ""
        if getattr(task, 'deadline', None):
            try:
                dt = datetime.fromisoformat(task.deadline)
                now = datetime.now()
                today = now.replace(hour=0, minute=0, second=0, microsecond=0)
                task_date = dt.replace(hour=0, minute=0, second=0, microsecond=0)
                
                hard_indicator = f"  {Fore.RED}⚠{Style.RESET_ALL}" if getattr(task, 'deadline_type', None) == "hard" else ""
                
                if dt < now:
                    # Past
                    date_formatted = dt.strftime('%b %d')
                    dl_text = f"Overdue — {date_formatted}"
                    deadline_str = f" · {Fore.RED}{dl_text}{Style.RESET_ALL}{hard_indicator}"
                elif task_date == today:
                    # Today
                    time_formatted = dt.strftime('%I:%M %p').lstrip('0')
                    dl_text = f"Today at {time_formatted}"
                    deadline_str = f" · {Fore.YELLOW}{dl_text}{Style.RESET_ALL}{hard_indicator}"
                elif task_date == today + timedelta(days=1):
                    # Tomorrow
                    time_formatted = dt.strftime('%I:%M %p').lstrip('0')
                    dl_text = f"Tomorrow at {time_formatted}"
                    deadline_str = f" · {Fore.MAGENTA}{dl_text}{Style.RESET_ALL}{hard_indicator}"
                else:
                    # Future
                    date_formatted = dt.strftime('%a %d %b')
                    time_formatted = dt.strftime('%I:%M %p').lstrip('0')
                    dl_text = f"{date_formatted}, {time_formatted}"
                    deadline_str = f" · {Fore.GREEN}{dl_text}{Style.RESET_ALL}{hard_indicator}"
            except ValueError:
                deadline_str = f" · {Fore.WHITE}{Style.DIM}{task.deadline}{Style.RESET_ALL}"
                
        # Build the final string
        id_str = f"{Fore.GREEN}#{task.id}{Style.RESET_ALL}"
        base = f"{id_str} · {title_color}{task.title}{Style.RESET_ALL}{duration_str}{priority_str}{tags_str}{pressure_suffix}{postpone_suffix}\n     Deadline: {deadline_str.strip(' ·')}"
        if not getattr(task, 'deadline', None):
            base = f"{id_str} · {title_color}{task.title}{Style.RESET_ALL}{duration_str}{priority_str}{tags_str}{pressure_suffix}{postpone_suffix}"
        
        base += hard_pressure_line
        
        if task.completed:
            # Overwrite base format for completed tasks to match old style but dim
            base = f"{id_str} · {title_color}{task.title}{Style.RESET_ALL}{duration_str}{priority_str}{tags_str}{deadline_str}"
            print(f"{Fore.GREEN}✓{Style.RESET_ALL} {Style.DIM}{base}{Style.RESET_ALL}")
        elif task.dropped_at or task.offloaded_at:
            base = f"{id_str} · {title_color}{task.title}{Style.RESET_ALL}{duration_str}{priority_str}{tags_str}{deadline_str}"
            print(f"{Fore.RED}x{Style.RESET_ALL} {Style.DIM}{base}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}○{Style.RESET_ALL} {base}")
            
        shown += 1
    
    print(f"\n{Style.DIM}Total: {len(filtered_tasks)} task(s){Style.RESET_ALL}")

    # Gentle UX hint for sorting (only when useful)
    if not sort_by and len(filtered_tasks) > 5:
        Messenger.note(
            "Tip: Use --sort priority or --sort due to organize tasks."
        )



def _generate_dopamine(task_id: int = None, increment: bool = True) -> dict:
    """
    Unified Dopamine Engine: generates variable reward stats and persists
    a single source-of-truth stats file (user_stats.json).
    """
    import random
    velocity = random.randint(8, 25)
    stats_file = storage.data_dir / "user_stats.json"
    
    # Load existing stats
    stats = {
        'daily_completions': 0,
        'daily_streak': 0,
        'last_completion_date': '',
        # Legacy Phase 2 keys kept for backward compatibility (synced below)
        'cycles_today': 0,
        'last_cycle_date': '',
        'streak_days': 0,
    }
    if stats_file.exists():
        try:
            with open(stats_file, 'r') as f:
                loaded = json.load(f)
                stats.update(loaded)
        except:
            pass

    today = datetime.now().strftime('%Y-%m-%d')

    if increment:
        if stats.get('last_completion_date') == today:
            stats['daily_completions'] = stats.get('daily_completions', 0) + 1
        else:
            last_date_str = stats.get('last_completion_date', '')
            if last_date_str:
                try:
                    last_date = datetime.strptime(last_date_str, '%Y-%m-%d')
                    delta = (datetime.now() - last_date).days
                    if delta == 1:
                        stats['daily_streak'] = stats.get('daily_streak', 0) + 1
                    else:
                        stats['daily_streak'] = 1 
                except:
                    stats['daily_streak'] = 1
            else:
                stats['daily_streak'] = 1

            stats['daily_completions'] = 1
            stats['last_completion_date'] = today

        # Synchronize Phase 2 legacy keys
        stats['cycles_today'] = stats['daily_completions']
        stats['last_cycle_date'] = today
        stats['streak_days'] = stats['daily_streak']

        try:
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2)
        except:
            pass

    return {
        "velocity": velocity,
        "streak": stats['daily_streak'],
        "daily_completions": stats['daily_completions'],
    }


def complete_task(task_id: int):
    """Mark a task as completed and trigger Dopamine Engine."""
    tasks = storage.load_tasks()

    for task in tasks:
        if task.id == task_id:
            # If already done, we STILL want the dopamine payload (current stats) 
            # but without incrementing the streak/count again.
            if task.completed:
                dopamine = _generate_dopamine(task_id, increment=False)
                streak = dopamine['streak']
                daily = dopamine['daily_completions']
                day_word = "Day" if streak == 1 else "Days"
                
                try:
                    print(f"\n[!] TASK ALREADY COMPLETED (ID: {task_id})")
                    print(f"✦ Execution Streak: {streak} {day_word}  |  Today: {daily} mission(s) complete")
                except: pass
                return dopamine

            task.completed = True
            task.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            storage.save_tasks(tasks)

            dopamine = _generate_dopamine(task_id, increment=True)
            streak = dopamine['streak']
            velocity = dopamine['velocity']
            daily = dopamine['daily_completions']
            day_word = "Day" if streak == 1 else "Days"

            try:
                print(f"\n[✓] MISSION SUCCESS (ID: {task_id})")
                print(f"✦ +{velocity}% Execution Velocity")
                print(f"✦ Execution Streak: {streak} {day_word}  |  Today: {daily} mission(s) complete")
            except Exception:
                pass 

            return dopamine

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
    """Show comprehensive help with premium formatting."""
    print(f"""
  TaskFlow v3.2.0 — Calm, Powerful CLI Task Assistant
  {"─" * 60}

  CORE COMMANDS:
    add                     Add mission interactively
    list                    List your mission board (--todo, --done)
    view <id>               View detailed mission brief
    edit <id>               Recalibrate mission parameters
    complete <id>           Mark mission as [V] SUCCESS
    undo <id>               Re-open mission to [ ] TODO
    delete <id>             Purge mission from record

  CHRONO & FOCUS (v2.0):
    focus --id <id>         Initiate Focus Flow (default 25m)
    focus --status          Check active focus telemetry
    focus --end             Gracefully terminate focus session
    schedule <id> <date>    Assign mission to timeline (YYYY-MM-DD/today)
    today                   Review missions assigned for today

  ENHANCED TELEMETRY:
    note <id>               Append intelligence to mission
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

def list_ids() -> None:
    """Display only task IDs (power-user helper)."""
    tasks = storage.load_tasks()

    if not tasks:
        Messenger.empty_list()
        return

    print(" ".join(str(task.id) for task in tasks))



# =========================================================
# TIME MANAGEMENT COMMANDS (NEW for v2.0)
# =========================================================

def focus_task(task_id: int, minutes: int = 25, 
               block_sites: list = None, block_apps: list = None,
               mode: str = "gentle", force: bool = False):
    """Start focus on a task with optional distraction blocking.
    
    Args:
        task_id: ID of task to focus on
        minutes: Focus duration in minutes
        block_sites: List of websites to block/avoid
        block_apps: List of applications to block/avoid
        mode: "gentle" (reminders) or "strict" (actual blocking)
    """
    tasks = storage.load_tasks()
    
    for task in tasks:
        if task.id == task_id:
            if task.completed:
                Messenger.note("This task is already completed.")
                return False
            
            # Check if already in focus
            if focus_manager.is_focus_active():
                Messenger.note("A focus session is already active. End it first.")
                return False
                
            # --- BLOCKLIST INTEGRATION ---
            if (mode in ["strict", "gentle"]) and not block_sites:
                saved_sites = blocklist_manager.load_sites()
                if saved_sites:
                    print("\n🛡️  Stored Blocklist:")
                    for i, site in enumerate(saved_sites, 1):
                        print(f"  {i}. {site}")
                    print("\nSelect websites to block (e.g., '1 2 5', 'all', or press Enter to skip):")
                    choice = get_valid_input("Selection: ").strip().lower()
                    if choice == 'all':
                        block_sites = saved_sites
                    elif choice:
                        selected_indices = []
                        for part in choice.split():
                            if part.isdigit():
                                idx = int(part)
                                if 1 <= idx <= len(saved_sites):
                                    selected_indices.append(idx - 1)
                        if selected_indices:
                            block_sites = [saved_sites[i] for i in selected_indices]
            
            if block_sites:
                saved_sites = blocklist_manager.load_sites()
                new_sites = [s for s in block_sites if s not in saved_sites]
                if new_sites:
                    if confirm_action(f"\nSave {len(new_sites)} new site(s) to your persistent blocklist?"):
                        blocklist_manager.add_sites(new_sites)
                        print("   ✅ Saved to blocklist.")
            # -----------------------------
            
            # Start focus with blocking
            success = focus_manager.start_focus_session(
                task_id, task.title, 
                task_notes=task.notes or "",
                priority=task.priority or "medium",
                minutes=minutes, 
                sites=block_sites, apps=block_apps, mode=mode
            )
            
            if success:
                print(f"\n🎯 Now focusing on: {task.title}")
                if block_sites or block_apps:
                    print("   Distraction blocking activated!")
                    
                    # Spawn background unblocker
                    try:
                        import subprocess
                        import os
                        
                        # Find the background script
                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        cli_dir = os.path.dirname(current_dir)
                        bg_script = os.path.join(cli_dir, "taskflow", "taskflow_bg_unblocker.py")
                        
                        if os.path.exists(bg_script):
                            # Start detached process depending on OS
                            creationflags = 0
                            if sys.platform == "win32":
                                creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
                                
                            subprocess.Popen(
                                [sys.executable, bg_script, str(minutes)],
                                creationflags=creationflags,
                                close_fds=True,
                                cwd=cli_dir
                            )
                    except Exception as e:
                        print(f"   ⚠️  Background auto-unblocker failed to start: {e}")
                        
                open_web_ui(force=False)
                return True
            return False
    
    Messenger.task_not_found(task_id)
    return False

def check_focus():
    """Check current focus status with blocking info."""
    status = focus_manager.get_focus_status()
    
    if not status["focus_active"]:
        Messenger.note("No active focus session.")
        
        # Check if blocking is still active (shouldn't happen, but safety)
        if focus_manager.blocker and focus_manager.blocker.is_active:
            print("⚠️  Warning: Blocking is still active but no focus session!")
            print("   Use 'taskflow focus-end' to clean up.")
        return
    
    # Show focus info
    print(f"\n🎯 Currently focusing on:")
    print(f"   Task: {status['task_title']} (ID: {status['task_id']})")
    print(f"   Time left: {status['minutes_left']} minutes")
    end_time = datetime.now() + timedelta(minutes=status['minutes_left'])
    print(f"   Ends at: {end_time.strftime('%H:%M')}")
    
    # Show blocking info if active
    if status["blocking_active"]:
        mode_display = "🚫 STRICT" if status["blocking_mode"] == "strict" else "🔔 GENTLE"
        print(f"\n🛡️  Blocking: {mode_display} MODE")
        
        if status["blocked_items"]["sites"]:
            sites = status["blocked_items"]["sites"][:3]
            more = len(status["blocked_items"]["sites"]) - 3
            site_text = ', '.join(sites)
            if more > 0:
                site_text += f" (+{more} more)"
            print(f"   Websites: {site_text}")
        
        if status["blocked_items"]["apps"]:
            apps = status["blocked_items"]["apps"][:3]
            more = len(status["blocked_items"]["apps"]) - 3
            app_text = ', '.join(apps)
            if more > 0:
                app_text += f" (+{more} more)"
            print(f"   Applications: {app_text}")
        
        if status["blocking_mode"] == "gentle":
            print("   Mode: Gentle reminders only")
        else:
            print("   Mode: Full blocking active")

def end_focus(force=False):
    """End the current focus session."""
    if not focus_manager.is_focus_active():
        Messenger.note("No active focus session to end.")
        return False
        
    status = time_tracker.check_focus()
    # Check if we are ending prematurely
    if status and status.get('status') == 'active' and not force:
        minutes_left = status.get('remaining_minutes', 0)
        session_data = status.get('session') or time_tracker.active_session or {}
        task_title = session_data.get('task_title', 'Task')
        
        print(f"\n🌱 Pausing focus.")
        print(f"You still have {minutes_left} minutes left on: '{task_title}'")
        print("\nAre you taking a purposeful break?")
        print("(Type 'resume' to keep working, or 'stop' to end the session early)")
        
        while True:
            choice = get_valid_input("\nChoice: ").strip().lower()
            if choice == "resume":
                print("\n🎯 Resuming focus. You've got this!")
                return False
            elif choice == "stop":
                print("\n🛑 Session ended early.")
                break
            else:
                print("Please type 'resume' or 'stop'.")
    
    return focus_manager.end_focus_session()


def focus_blocking_status():
    """Show detailed blocking status."""
    if not focus_manager.blocker:
        focus_manager.init_blocker("gentle")
    
    if focus_manager.blocker:
        status = focus_manager.blocker.get_status()
        
        print("\n🛡️  BLOCKING SYSTEM STATUS")
        print("=" * 40)
        
        # System info
        sys_info = SystemDetector.get_system_info()
        print(f"Platform: {sys_info['os'].upper()}")
        print(f"Admin rights: {'✅ Yes' if sys_info['admin'] else '❌ No'}")
        print(f"Python: {sys_info['python_version']}")
        
        # Blocker status
        print(f"\nBlocker: {type(focus_manager.blocker).__name__}")
        print(f"Active: {'✅ Yes' if status['active'] else '❌ No'}")
        
        if status['active']:
            print(f"Started: {status['since'].strftime('%H:%M:%S')}")
            print(f"Mode: {'Gentle reminders' if status.get('gentle_mode') else 'Full blocking'}")
            
            if status['blocked_sites']:
                print(f"\nBlocked Websites ({len(status['blocked_sites'])}):")
                for i, site in enumerate(status['blocked_sites'][:5], 1):
                    print(f"  {i}. {site}")
                if len(status['blocked_sites']) > 5:
                    print(f"  ... and {len(status['blocked_sites']) - 5} more")
            
            if status['blocked_apps']:
                print(f"\nBlocked Applications ({len(status['blocked_apps'])}):")
                for i, app in enumerate(status['blocked_apps'][:5], 1):
                    print(f"  {i}. {app}")
                if len(status['blocked_apps']) > 5:
                    print(f"  ... and {len(status['blocked_apps']) - 5} more")
        else:
            print("\nNo blocking active. Start a focus session with --block-sites or --block-apps")
    
    print("\n" + "=" * 40)

def test_blocking(mode="gentle"):
    """Test the blocking system."""
    print(f"\n🧪 TESTING BLOCKING SYSTEM ({mode.upper()} MODE)")
    print("=" * 50)
    
    # Initialize blocker
    focus_manager.init_blocker(mode)
    
    if not focus_manager.blocker:
        print("❌ Failed to initialize blocker")
        return False
    
    # Test sites and apps
    test_sites = ["facebook.com", "youtube.com", "twitter.com"]
    test_apps = ["discord", "spotify"]
    
    print(f"\nTest Configuration:")
    print(f"  Mode: {mode}")
    print(f"  Test websites: {', '.join(test_sites)}")
    print(f"  Test apps: {', '.join(test_apps)}")
    
    # Start blocking
    print(f"\n📢 Starting blocking test...")
    focus_manager.blocker.start_focus(
        sites=test_sites, 
        apps=test_apps, 
        gentle_mode=(mode == "gentle")
    )
    
    # Show status
    status = focus_manager.blocker.get_status()
    print(f"✅ Blocking active: {status['active']}")
    print(f"   Mode: {'Gentle' if status.get('gentle_mode') else 'Strict'}")
    
    if mode == "strict" and not SystemDetector.is_admin():
        print("\n⚠️  Note: Strict mode requires administrator privileges.")
        print("   Run 'taskflow' as Administrator for full blocking.")
    
    # Wait a bit (for demonstration)
    print("\n⏳ Blocking test in progress for 10 seconds...")
    print("   (Press Ctrl+C to cancel)")
    
    try:
        for i in range(10, 0, -1):
            print(f"   {i}...", end='\r')
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Test cancelled by user")
    
    # End blocking
    print("\n🛑 Ending blocking test...")
    focus_manager.blocker.end_focus()
    
    print("✅ Test completed successfully!")
    print("\n" + "=" * 50)
    return True

# ============================================================================
# EMERGENCY CLEANUP COMMAND
# ============================================================================

def emergency_cleanup():
    """Emergency cleanup if blocking gets stuck - Windows specific."""
    print("\n" + "🚨" * 10)
    print("🚨 EMERGENCY CLEANUP - WINDOWS")
    print("🚨" * 10)
    
    print("\n📋 This will:")
    print("   1. Remove ALL TaskFlow blocking from hosts file")
    print("   2. Flush DNS cache")
    print("   3. Reset focus system")
    print("   4. Suggest browser restart")
    
    # Check if admin
    from .system_detector import SystemDetector
    is_admin = SystemDetector.is_admin()
    
    if not is_admin:
        print("\n⚠️  WARNING: Not running as Administrator!")
        print("   Some cleanup may not work properly.")
        print("   Run Command Prompt as Admin for full cleanup.")
    
    try:
        # 1. END ANY ACTIVE FOCUS SESSION
        print("\n1. Ending focus sessions...")
        if focus_manager.is_focus_active():
            print("   Ending active focus...")
            time_tracker.end_focus()
        
        # 2. CLEAN HOSTS FILE
        print("\n2. Cleaning hosts file...")
        hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
        
        try:
            # Read current hosts file
            with open(hosts_path, 'r') as f:
                lines = f.readlines()
            
            # Filter out TaskFlow lines
            original_count = len(lines)
            cleaned_lines = []
            in_taskflow_block = False
            removed_count = 0
            
            for line in lines:
                # Start of TaskFlow block
                if "# TaskFlow" in line and ("Focus Mode" in line or "Blocked Sites" in line):
                    in_taskflow_block = True
                    print(f"   Found TaskFlow block: {line.strip()}")
                    removed_count += 1
                    continue
                
                # Inside TaskFlow block
                if in_taskflow_block:
                    # Check if this is a blocking line
                    if "127.0.0.1" in line and any(site in line for site in [
                        "youtube.com", "facebook.com", "twitter.com", 
                        "instagram.com", "reddit.com", "netflix.com",
                        "tiktok.com", "discord.com", "whatsapp.com"
                    ]):
                        print(f"   Removing: {line.strip()}")
                        removed_count += 1
                        continue
                    
                    # End of block (empty line or new section)
                    if line.strip() == "" or (line.strip().startswith("#") and "TaskFlow" not in line):
                        in_taskflow_block = False
                        # Skip empty line after block
                        if line.strip() == "":
                            continue
                
                # Keep this line
                cleaned_lines.append(line)
            
            # Write cleaned file if we found TaskFlow entries
            if removed_count > 0:
                with open(hosts_path, 'w') as f:
                    f.writelines(cleaned_lines)
                print(f"   ✅ Removed {removed_count} TaskFlow entries")
            else:
                print("   ✅ No TaskFlow entries found")
        
        except PermissionError:
            print("   ❌ Permission denied! Need Administrator rights.")
            print("   Run: taskflow cleanup (as Administrator)")
        except Exception as e:
            print(f"   ⚠️  Could not clean hosts file: {e}")
        
        # 3. FLUSH DNS CACHE
        print("\n3. Flushing DNS cache...")
        try:
            import subprocess
            result = subprocess.run(
                ["ipconfig", "/flushdns"],
                capture_output=True,
                text=True,
                shell=True
            )
            
            if result.returncode == 0:
                print("   ✅ DNS cache flushed successfully")
            else:
                print(f"   ⚠️  DNS flush returned: {result.returncode}")
                if result.stderr:
                    print(f"   Error: {result.stderr[:100]}")
        
        except Exception as e:
            print(f"   ⚠️  Could not flush DNS: {e}")
        
        # 4. RESET FOCUS MANAGER
        print("\n4. Resetting focus system...")
        try:
            # Force end any blocker
            if focus_manager.blocker:
                focus_manager.blocker.is_active = False
                focus_manager.blocker.blocked_sites = []
                focus_manager.blocker.blocked_apps = []
                print("   ✅ Blocker reset")
            
            # Reset focus manager
            focus_manager.active_focus_task = None
            focus_manager.blocked_at_start = None
            focus_manager.focus_start_time = None
            print("   ✅ Focus manager reset")
        
        except Exception as e:
            print(f"   ⚠️  Could not reset focus: {e}")
        
        # 5. CHECK FOR COMMON BLOCKED SITES
        print("\n5. Checking common blocked sites...")
        common_sites = [
            "youtube.com",
            "www.youtube.com", 
            "facebook.com",
            "www.facebook.com",
            "twitter.com",
            "www.twitter.com",
            "instagram.com",
            "www.instagram.com",
            "reddit.com",
            "www.reddit.com"
        ]
        
        try:
            with open(hosts_path, 'r') as f:
                content = f.read()
            
            still_blocked = []
            for site in common_sites:
                if site in content and "127.0.0.1" in content:
                    still_blocked.append(site)
            
            if still_blocked:
                print(f"   ⚠️  Still blocked: {', '.join(still_blocked[:3])}")
                if len(still_blocked) > 3:
                    print(f"   ... and {len(still_blocked) - 3} more")
                print("   Manual fix required (edit hosts file)")
            else:
                print("   ✅ No common sites blocked")
        
        except:
            print("   ⚠️  Could not check blocked sites")
        
        # FINAL INSTRUCTIONS
        print("\n" + "✅" * 10)
        print("✅ CLEANUP COMPLETE")
        print("✅" * 10)
        
        print("\n🎯 NEXT STEPS:")
        print("   1. RESTART YOUR BROWSER COMPLETELY")
        print("      (Close ALL browser windows, not just tabs)")
        print("   2. Test previously blocked sites")
        print("   3. If still blocked, run this as Administrator")
        
        if not is_admin:
            print("\n⚠️  IMPORTANT: Run as Administrator for full cleanup!")
            print("   Right-click Command Prompt → 'Run as administrator'")
        
        return True
        
    except Exception as e:
        print(f"\n❌ EMERGENCY CLEANUP FAILED: {e}")
        print("\n🔧 MANUAL CLEANUP REQUIRED:")
        print("   1. Run Command Prompt as Administrator")
        print("   2. Type: notepad C:\\Windows\\System32\\drivers\\etc\\hosts")
        print("   3. Delete ALL lines containing:")
        print("      - 'TaskFlow'")
        print("      - 'youtube.com'")
        print("      - 'facebook.com'")
        print("      - Other blocked sites")
        print("   4. Save file")
        print("   5. Type: ipconfig /flushdns")
        print("   6. Restart browser completely")
        return False


def __parse_date(date_str: str) -> str:
    if not date_str: return datetime.now().strftime("%Y-%m-%d")
    date_str = date_str.lower()
    if date_str == 'today': return datetime.now().strftime("%Y-%m-%d")
    if date_str == 'tomorrow': return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    datetime.strptime(date_str, "%Y-%m-%d") # Validate format
    return date_str

def schedule_task(task_id: int, date_str: str) -> bool:
    """Schedule a task to the Execution Engine Timeline."""
    tasks = storage.load_tasks()
    task_exists = any(t.id == task_id for t in tasks)
    if not task_exists:
        Messenger.task_not_found(task_id)
        return False
        
    try:
        scheduled_date = __parse_date(date_str)
        mapping = storage.load_timeline()
        mapping[str(task_id)] = scheduled_date
        storage.save_timeline(mapping)
        Messenger.success(f"Task #{task_id} logically deployed to {scheduled_date}")
        return True
    except ValueError:
        Messenger.careful("Invalid date format. Use YYYY-MM-DD, 'today', or 'tomorrow'.")
        return False

def set_prime_target(task_id: int, date_str: str = 'today') -> bool:
    """Set a task as the single [PRIME TARGET] for a given date."""
    if not date_str: date_str = 'today'
    tasks = storage.load_tasks()
    task_exists = any(t.id == task_id for t in tasks)
    if not task_exists:
        Messenger.task_not_found(task_id)
        return False
        
    try:
        scheduled_date = __parse_date(date_str)
        prime_key = f"{scheduled_date}_prime"
        mapping = storage.load_timeline()
        
        # Enforce Prime Target Protocol (One Frog Per Day)
        for tid, d_key in mapping.items():
            if d_key == prime_key and str(tid) != str(task_id):
                Messenger.careful(f"Task #{tid} is ALREADY the Prime Target for {scheduled_date}.")
                print("Only ONE Prime Target allowed per day. Please reconsider.")
                return False
                
        mapping[str(task_id)] = prime_key
        storage.save_timeline(mapping)
        Messenger.success(f"🎯 Task #{task_id} is now your [PRIME TARGET] for {scheduled_date}")
        return True
    except ValueError:
        Messenger.careful("Invalid date format. Use YYYY-MM-DD, 'today', or 'tomorrow'.")
        return False

def render_timeline() -> None:
    """Render a 7-day tactical terminal timeline."""
    tasks = storage.load_tasks()
    mapping = storage.load_timeline()
    
    # Create quick lookup map for tasks
    task_dict = {str(t.id): t for t in tasks}
    
    # Calculate next 7 days
    start_date = datetime.now()
    dates = [(start_date + timedelta(days=i)) for i in range(7)]
    
    print("\n   [ TACTICAL TIMELINE (NEXT 7 DAYS) ]\n")
    
    for d in dates:
        d_str = d.strftime("%Y-%m-%d")
        d_label = d.strftime("%A, %b %d")
        print(f"─ {d_label} {'─' * (50 - len(d_label))}")
        
        # Check Prime Target
        prime_found = False
        for tid, d_key in mapping.items():
            if d_key == f"{d_str}_prime":
                tsk = task_dict.get(tid)
                if tsk:
                    print(f"  [★ PRIME TARGET] {tsk.title} (ID:{tid})")
                    prime_found = True
                    break
        
        if not prime_found:
            print("  [ ] No Prime Target assigned.")
            
        # Standard Tasks
        has_standard = False
        for tid, d_key in mapping.items():
            if d_key == d_str:
                tsk = task_dict.get(tid)
                if tsk:
                    if not has_standard:
                        print("\n  Scheduled Missions:")
                    print(f"   • {tsk.title} (ID:{tid}) [{tsk.priority.upper()}]")
                    has_standard = True
                    
        print() # Padding between days

def show_today_tasks() -> None:
    """Show today's scheduled tasks based on the timeline mapping."""
    today = datetime.now().strftime("%Y-%m-%d")
    tasks = storage.load_tasks()
    mapping = storage.load_timeline()
    
    today_tasks = []
    prime_task = None
    
    for task in tasks:
        d_key = mapping.get(str(task.id))
        if d_key == f"{today}_prime":
            prime_task = task
        elif d_key == today:
            today_tasks.append(task)
            
    print(f"\n📅 Today's Active Assignments ({datetime.now().strftime('%A, %b %d')}):")
    
    if prime_task:
        print(f"\n  🎯 [PRIME TARGET]\n    #{prime_task.id}: {prime_task.title} [{prime_task.priority.upper()}]")
    else:
        print("\n  🎯 [PRIME TARGET] -> Not Assigned. Run 'taskflow prime <id>' to prioritize.")

    if today_tasks:
        print("\n  📋 Missions:")
        for task in today_tasks:
            print(f"    #{task.id}: {task.title} [{task.priority.upper()}]")
    elif not prime_task:
        Messenger.note("\nNo tasks active for today.")


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

def manage_blocklist(action: str, sites: list = None, indices: list = None):
    """Manage the persistent blocklist."""
    if action == "list":
        saved = blocklist_manager.load_sites()
        if not saved:
            Messenger.note("Your blocklist is empty.")
            return
        print("\n🛡️  Persistent Blocklist:")
        for i, site in enumerate(saved, 1):
            print(f"  [{i}] {site}")
        print(f"\nTotal: {len(saved)} websites")
        print(f"💡 Hint: You can manually edit this at {blocklist_manager.blocklist_file}")
    
    elif action == "add" and sites:
        added = blocklist_manager.add_sites(sites)
        Messenger.success(f"Added {len(sites)} site(s). Total in blocklist: {len(added)}")
        
    elif action == "remove" and indices:
        remaining = blocklist_manager.remove_sites(indices)
        Messenger.success(f"Removed {len(indices)} site(s). Remaining: {len(remaining)}")
        
    elif action == "edit":
        import subprocess
        import sys
        path = blocklist_manager.blocklist_file
        print(f"Opening blocklist file: {path}")
        if sys.platform == "win32":
            subprocess.run(["notepad", str(path)])
        elif sys.platform == "darwin":
            subprocess.run(["open", "-e", str(path)])
        else:
            subprocess.run(["nano", str(path)])

def normalize_priority(priority: str) -> str:
    """Normalize priority input to Low / Medium / High."""
    if not priority:
        return "Medium"
    
    priority = priority.strip().lower()
    
    priority_map = {
        'high': 'Critical', 'h': 'Critical', 'critical': 'Critical',
        'medium': 'Strategic', 'm': 'Strategic', 'strategic': 'Strategic',
        'low': 'Noise', 'l': 'Noise', 'noise': 'Noise',
        'purge': 'Purge', 'p': 'Purge'
    }
    
    return priority_map.get(priority, 'Strategic')

def run_today_view():
    """Show today's tasks chronologically with Now Window."""
    handle_missed_tasks()
    
    tasks = storage.load_tasks()
    timeline = storage.load_timeline()
    
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    today_task_ids = {int(tid) for tid, tslot in timeline.items() if tslot.startswith(today_str)}
    
    today_tasks = []
    
    for task in tasks:
        if not task.completed and (task.dropped_at or task.offloaded_at):
            continue
            
        included = False
        task_dt = None
        
        if task.deadline:
            try:
                dt = datetime.fromisoformat(task.deadline)
                if dt.strftime('%Y-%m-%d') == today_str:
                    included = True
                    task_dt = dt
            except ValueError:
                pass
                
        if not included and not task.deadline and not task.completed:
            if task.created_at and task.created_at.startswith(today_str):
                included = True
                
        if not included and task.id in today_task_ids:
            included = True
            
        if included:
            today_tasks.append((task, task_dt))
            
    if not today_tasks:
        print("\nNo missions scheduled for today.\nAdd one: taskflow add\n")
        return
        
    if all(t[0].completed for t in today_tasks):
        print(Fore.GREEN + "\nAll missions complete. Excellent execution today.\n" + Style.RESET_ALL)
        return
        
    timed_tasks = [t for t in today_tasks if t[1] is not None]
    untimed_tasks = [t for t in today_tasks if t[1] is None]
    
    timed_tasks.sort(key=lambda t: t[1])
    
    priority_order = {"critical": 0, "strategic": 1, "noise": 2, "purge": 3, "high": 0, "medium": 1, "low": 2}
    untimed_tasks.sort(key=lambda t: priority_order.get((t[0].priority or "").lower(), 1))
    
    # Feature 8: The "Approaching" header
    pressure_counts = {2: 0, 3: 0}
    for task, dt in today_tasks:
        if not task.completed:
            p_level = get_pressure_level(task)
            if p_level in [2, 3]:
                pressure_counts[p_level] += 1
                
    total_pressure_tasks = pressure_counts[2] + pressure_counts[3]
    print()
    if total_pressure_tasks > 0:
        header_color = Fore.RED if pressure_counts[3] > 0 else Fore.YELLOW
        print(header_color + f"  ⚡ {total_pressure_tasks} task(s) need attention now." + Style.RESET_ALL)
        
    header_str = f" TODAY · {now.strftime('%A, %d %b')} "
    print(Fore.WHITE + Style.DIM + f"──{header_str}" + "─" * (50 - len(header_str) - 2) + Style.RESET_ALL)
    print()
    
    window_start = now - timedelta(minutes=45)
    window_end = now + timedelta(minutes=45)
    
    now_task = None
    next_task = None
    
    for task, dt in timed_tasks:
        if not task.completed:
            if window_start <= dt <= window_end:
                now_task = (task, dt)
                break
                
    if not now_task:
        for task, dt in timed_tasks:
            if not task.completed and dt > now:
                next_task = (task, dt)
                break
                
    for task, dt in timed_tasks:
        time_str = dt.strftime('%H:%M')
        
        row_color = Fore.WHITE
        prefix = "   "
        suffix = ""
        is_now = False
        is_next = False
        
        pressure_line = ""
        
        if task.completed:
            row_color = Fore.WHITE + Style.DIM
            prefix = "✓  "
            suffix = "   [done]"
        else:
            if now_task and task.id == now_task[0].id:
                row_color = Fore.WHITE + Style.BRIGHT
                prefix = "▶  "
                suffix = f"   {Fore.CYAN}[NOW ← you are here]{Style.RESET_ALL}"
                is_now = True
            elif next_task and task.id == next_task[0].id:
                row_color = Fore.WHITE + Style.BRIGHT
                prefix = "▶  "
                suffix = f"   {Fore.CYAN}[NEXT MISSION]{Style.RESET_ALL}"
                is_next = True
                
            # Feature 8 & 6C Integration
            p_level = get_pressure_level(task)
            if p_level > 0:
                td = dt - datetime.now()
                rem_str = format_time_remaining(td)
                if p_level == 3:
                    if getattr(task, 'deadline_type', None) == "hard":
                        row_color = Fore.RED + Style.BRIGHT
                    else:
                        row_color = Fore.YELLOW + Style.BRIGHT
                    if td.total_seconds() < 0:
                        suffix += f" · {Fore.RED + Style.BRIGHT}{rem_str}{Style.RESET_ALL}"
                    else:
                        suffix += f" · {Fore.RED + Style.BRIGHT}{rem_str} ⚠{Style.RESET_ALL}"
                    pressure_line = f"\n     ··· {Fore.RED + Style.BRIGHT}⚠ Execution window closing in {rem_str.replace(' left', '')}.{Style.RESET_ALL}"
                elif p_level == 2:
                    row_color = Fore.YELLOW
                    suffix += f" · {Fore.YELLOW + Style.BRIGHT}{rem_str}{Style.RESET_ALL}"
                    pressure_line = f"\n     ··· {Fore.YELLOW}Execution window closing in {rem_str.replace(' left', '')}.{Style.RESET_ALL}"
                elif p_level == 1:
                    suffix += f" · {Fore.YELLOW}{rem_str}{Style.RESET_ALL}"
            
            if task.postpone_count >= 5:
                suffix += f"  {Fore.RED}(postponed ×{task.postpone_count}) ⚠⚠{Style.RESET_ALL}"
            elif task.postpone_count >= 3:
                suffix += f"  {Fore.YELLOW}(postponed ×{task.postpone_count}) ⚠{Style.RESET_ALL}"
            elif task.postpone_count == 2:
                suffix += f"  {Fore.YELLOW}(postponed ×2){Style.RESET_ALL}"
            
            if getattr(task, 'deadline_type', None) == "hard":
                suffix += f"  {Fore.RED}⚠ HARD{Style.RESET_ALL}"
            
        print(row_color + f"{prefix}{time_str}   {task.title:<26}{Style.RESET_ALL}{suffix}")
        
        if is_now or is_next:
            duration_part = f" · {task.duration} estimated" if task.duration else ""
            tags_part = f" · #{', #'.join(task.tags)}" if task.tags else ""
            print(row_color + f"           Priority: {task.priority}{tags_part}{duration_part}" + Style.RESET_ALL)
            
        if pressure_line:
            print(pressure_line)
            
    if untimed_tasks:
        print("\n  No time set:")
        for task, _ in untimed_tasks:
            if task.completed:
                continue
            priority_tags = f"{task.priority}"
            if task.tags:
                priority_tags += f" · #{', #'.join(task.tags)}"
                
            suffix = ""
            p_level = get_pressure_level(task)
            pressure_line = ""
            
            if p_level > 0 and task.deadline:
                try:
                    td = datetime.fromisoformat(task.deadline) - datetime.now()
                    rem_str = format_time_remaining(td)
                    if p_level == 3:
                        if td.total_seconds() < 0:
                            suffix += f" · {Fore.RED + Style.BRIGHT}{rem_str}{Style.RESET_ALL}"
                        else:
                            suffix += f" · {Fore.RED + Style.BRIGHT}{rem_str} ⚠{Style.RESET_ALL}"
                        pressure_line = f"\n        ··· {Fore.RED + Style.BRIGHT}⚠ Execution window closing in {rem_str.replace(' left', '')}.{Style.RESET_ALL}"
                    elif p_level == 2:
                        suffix += f" · {Fore.YELLOW + Style.BRIGHT}{rem_str}{Style.RESET_ALL}"
                        pressure_line = f"\n        ··· {Fore.YELLOW}Execution window closing in {rem_str.replace(' left', '')}.{Style.RESET_ALL}"
                    elif p_level == 1:
                        suffix += f" · {Fore.YELLOW}{rem_str}{Style.RESET_ALL}"
                except ValueError:
                    pass
            
            if task.postpone_count >= 5:
                suffix += f"  {Fore.RED}(postponed ×{task.postpone_count}) ⚠⚠{Style.RESET_ALL}"
            elif task.postpone_count >= 3:
                suffix += f"  {Fore.YELLOW}(postponed ×{task.postpone_count}) ⚠{Style.RESET_ALL}"
            elif task.postpone_count == 2:
                suffix += f"  {Fore.YELLOW}(postponed ×2){Style.RESET_ALL}"
                
            if getattr(task, 'deadline_type', None) == "hard":
                suffix += f"  {Fore.RED}⚠ HARD{Style.RESET_ALL}"
                
            print(f"     ·  {task.title:<30}  {priority_tags}{suffix}")
            if pressure_line:
                print(pressure_line)
            
    print(Fore.WHITE + Style.DIM + "─" * 50 + Style.RESET_ALL)
    
    target = now_task or next_task
    if target:
        t, dt = target
        title_color = Fore.CYAN + Style.BRIGHT
        if now_task:
            print(title_color + f"Next mission: {t.title}" + Style.RESET_ALL)
        else:
            print(title_color + f"Upcoming mission: {t.title}" + Style.RESET_ALL)
            
        time_diff = int((now - dt).total_seconds() / 60)
        
        started_str = ""
        if time_diff > 0:
            started_str = f"Started {time_diff} minutes ago"
        elif time_diff == 0:
            started_str = "Starts now"
        else:
            started_str = f"Starts in {abs(time_diff)} minutes"
            
        dur_str = f" · {t.duration} estimated" if t.duration else ""
        
        ends_str = ""
        if t.duration:
            import re
            m = re.match(r'(\d+)(m|h)', t.duration)
            if m:
                val = int(m.group(1))
                unit = m.group(2)
                mins = val if unit == 'm' else val * 60
                end_dt = dt + timedelta(minutes=mins)
                ends_str = f" · ends ~{end_dt.strftime('%I:%M %p').lstrip('0')}"
                
        print(f"{started_str}{dur_str}{ends_str}")
    else:
        uncompleted_timed = [t for t in timed_tasks if not t[0].completed]
        if not uncompleted_timed and untimed_tasks:
            pass 
        elif not uncompleted_timed:
            pass
        else:
            print("All scheduled windows have passed.")
    print()


# =========================================================
# FEATURE 9: RECOVERY MODE
# =========================================================

def should_trigger_recovery() -> bool:
    """Evaluate if the user's day has collapsed."""
    tasks = storage.load_tasks()
    timeline = storage.load_timeline()
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # Condition 1: 3+ tasks missed today
    missed_count = 0
    now = datetime.now()
    
    for task in tasks:
        if not task.completed and task.deadline:
            try:
                dt = datetime.fromisoformat(task.deadline)
                if dt < now and dt.strftime('%Y-%m-%d') == today_str:
                    missed_count += 1
            except ValueError:
                pass
                
    if missed_count >= 3:
        return True
        
    # Condition 2: 5+ pending tasks scheduled before 12 PM today, and it is past 2 PM
    if now.hour >= 14:
        morning_pending = 0
        today_task_ids = {int(tid) for tid, tslot in timeline.items() if tslot.startswith(today_str)}
        
        for task in tasks:
            if not task.completed and task.id in today_task_ids:
                if task.deadline:
                    try:
                        dt = datetime.fromisoformat(task.deadline)
                        if dt.hour < 12:
                            morning_pending += 1
                    except ValueError:
                        pass
                        
        if morning_pending >= 5:
            return True
            
    return False


def select_recovery_tasks() -> List[Task]:
    """Select the 2 most critical tasks to salvage the day."""
    tasks = storage.load_tasks()
    timeline = storage.load_timeline()
    today_str = datetime.now().strftime('%Y-%m-%d')
    today_task_ids = {int(tid) for tid, tslot in timeline.items() if tslot.startswith(today_str)}
    
    today_pending = [t for t in tasks if not t.completed and t.id in today_task_ids]
    
    # 1. Hard deadlines today
    hard_deadlines = [t for t in today_pending if getattr(t, 'deadline_type', None) == 'hard']
    
    # 2. Critical/High priority today
    high_priority = [t for t in today_pending if (t.priority or "").lower() in ["critical", "high"] and t not in hard_deadlines]
    
    # 3. Quick wins (<= 30m)
    quick_wins = []
    for t in today_pending:
        if t not in hard_deadlines and t not in high_priority:
            if t.duration in ["15m", "30m"]:
                quick_wins.append(t)
                
    # 4. Remaining today
    remaining = [t for t in today_pending if t not in hard_deadlines and t not in high_priority and t not in quick_wins]
    
    pool = hard_deadlines + high_priority + quick_wins + remaining
    
    # If we don't have enough today tasks, pull from general backlog (high priority first)
    if len(pool) < 2:
        backlog_high = [t for t in tasks if not t.completed and t.id not in today_task_ids and (t.priority or "").lower() in ["critical", "high"]]
        pool.extend(backlog_high)
        
    return pool[:2]


def run_recovery_view():
    """Display the Recovery Dashboard."""
    state = storage.load_recovery_state()
    if not state.get('active'):
        return
        
    tasks = storage.load_tasks()
    mission_ids = state.get('mission_ids', [])
    recovery_tasks = [t for t in tasks if t.id in mission_ids and not t.completed]
    
    print(Fore.RED + "\n" + "═" * 60)
    print(" SYSTEM RECOVERY MODE INITIATED")
    print("═" * 60 + Style.RESET_ALL)
    print("\n" + Fore.WHITE + Style.DIM + "The schedule has collapsed. All other tasks are hidden." + Style.RESET_ALL)
    print("To salvage today, execute these missions:\n")
    
    if not recovery_tasks:
        print(Fore.GREEN + "Recovery missions complete! Run 'taskflow recover --exit' to return to normal." + Style.RESET_ALL)
        return
        
    for idx, t in enumerate(recovery_tasks, 1):
        print(f"  [{idx}]  " + Fore.WHITE + Style.BRIGHT + f"{t.title:<30}" + Style.RESET_ALL + f"  ·  {t.priority}  ·  {t.duration or 'Unknown time'}")
        
    print("\nOptions:")
    for t in recovery_tasks:
        print(f"  taskflow focus --id {t.id}")
    print(f"\n  taskflow recover --exit    {Style.DIM}(Abort recovery mode){Style.RESET_ALL}\n")


def command_recover(trigger: bool = False, exit_mode: bool = False):
    """Handle recovery commands."""
    state = storage.load_recovery_state()
    
    if exit_mode:
        if not state.get('active'):
            print("Not currently in Recovery Mode.")
            return
            
        # Log analytics
        log_entry = {
            "triggered_at": state.get('triggered_at'),
            "exited_at": datetime.now().isoformat(),
            "reason": state.get('reason'),
            "missions_assigned": len(state.get('mission_ids', [])),
            "missions_completed": sum(1 for t in storage.load_tasks() if t.id in state.get('mission_ids', []) and t.completed)
        }
        storage.append_recovery_log(log_entry)
        
        storage.save_recovery_state({"active": False})
        print(Fore.GREEN + "Recovery Mode deactivated. Standard schedule restored." + Style.RESET_ALL)
        return
        
    if trigger:
        if state.get('active'):
            print("Recovery Mode is already active.")
            return
            
        recovery_tasks = select_recovery_tasks()
        if not recovery_tasks:
            print("No pending tasks available for recovery.")
            return
            
        new_state = {
            "active": True,
            "triggered_at": datetime.now().isoformat(),
            "reason": "manual trigger",
            "mission_ids": [t.id for t in recovery_tasks]
        }
        storage.save_recovery_state(new_state)
        print(Fore.RED + "Recovery Mode manually engaged." + Style.RESET_ALL)
        run_recovery_view()
        return
        
    # Default: Show view if active, else print status
    if state.get('active'):
        run_recovery_view()
    else:
        print("System nominal. No recovery needed.")


def check_recovery_mode() -> bool:
    """Check if recovery mode should trigger or is active."""
    state = storage.load_recovery_state()
    if state.get('active'):
        return True
        
    if should_trigger_recovery():
        recovery_tasks = select_recovery_tasks()
        if recovery_tasks:
            new_state = {
                "active": True,
                "triggered_at": datetime.now().isoformat(),
                "reason": "auto trigger — day collapsed",
                "mission_ids": [t.id for t in recovery_tasks]
            }
            storage.save_recovery_state(new_state)
            return True
            
    return False

