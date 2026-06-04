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
    """Parse natural language date/time strings. Always returns timezone-naive datetime."""
    if not raw_string or not raw_string.strip():
        return None
        
    import re
    processed = raw_string.lower().strip()
    
    # "monday 17h" -> "monday 17:00"
    processed = re.sub(r'(?<!in )(?<!\+)\b(\d{1,2})h\b', r'\1:00', processed)
    
    # exact matches
    if processed == "tomorrow":
        processed = "tomorrow 9am"
    elif processed == "morning":
        processed = "tomorrow 9am"
    elif processed == "evening":
        processed = "today 6pm"
        
    # next day
    processed = re.sub(r'\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', r'\1', processed)
    
    dt = dateparser.parse(
        processed,
        settings={
            'PREFER_DATES_FROM': 'future',
            'PREFER_DAY_OF_MONTH': 'first',
            'DATE_ORDER': 'DMY',
            'RETURN_AS_TIMEZONE_AWARE': False,
            'TIMEZONE': 'local'
        }
    )
    if dt and dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt

def format_deadline_display(task: Task) -> str:
    if not getattr(task, 'deadline', None):
        return ""
    try:
        dt = datetime.fromisoformat(task.deadline)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        task_date = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        
        is_hard = (getattr(task, 'deadline_type', None) == "hard")
        hard_tag = " ⚠ HARD" if is_hard else ""
        
        if dt < now:
            # Overdue — Fix 4: drop the clock time once it's more than a day late
            if (now - dt).total_seconds() > 86400:
                date_formatted = dt.strftime('%b %d').replace(" 0", " ")
            else:
                date_formatted = dt.strftime('%b %d, %I:%M %p').replace(" 0", " ")
            color = Fore.RED
            res = f"OVERDUE — {date_formatted}"
        elif task_date == today:
            time_formatted = dt.strftime('%I:%M %p').lstrip('0')
            color = Fore.YELLOW
            res = f"Today at {time_formatted}"
        elif task_date == today + timedelta(days=1):
            time_formatted = dt.strftime('%I:%M %p').lstrip('0')
            color = Fore.CYAN
            res = f"Tomorrow at {time_formatted}"
        else:
            date_formatted = dt.strftime('%a %d %b, %I:%M %p').replace(" 0", " ")
            color = Fore.CYAN
            res = date_formatted
            
        hard_colored = f"{Fore.RED}{hard_tag}{Style.RESET_ALL}" if hard_tag else ""
        return f"{color}{res}{Style.RESET_ALL}{hard_colored}"
    except Exception:
        return f"{Fore.WHITE}{task.deadline}{Style.RESET_ALL}"

def log_behavior(event_dict):
    log_file = storage.data_dir / "behavior_log.jsonl"
    event_dict["ts"] = datetime.now().isoformat()
    try:
        storage.data_dir.mkdir(exist_ok=True)
        with open(log_file, "a") as f:
            f.write(json.dumps(event_dict) + "\n")
    except Exception:
        pass

def get_missed_tasks(tasks: List[Task]) -> List[Task]:
    missed = []
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    for task in tasks:
        if task.completed or getattr(task, 'dropped_at', None) or getattr(task, 'offloaded_at', None):
            continue
        if getattr(task, 'status', None) in ['completed', 'done', 'dropped', 'offloaded']:
            continue
        if not getattr(task, 'deadline', None):
            continue
        try:
            dl_dt = datetime.fromisoformat(task.deadline)
            if dl_dt.tzinfo is not None:
                dl_dt = dl_dt.replace(tzinfo=None)
            if dl_dt < now:
                if getattr(task, 'last_missed_prompt', None) != today_str:
                    missed.append((task, dl_dt))
        except ValueError:
            pass
            
    def missed_sort_key(item):
        t, dl_dt = item
        is_hard = (getattr(t, 'deadline_type', None) == "hard")
        return (0 if is_hard else 1, dl_dt)
        
    missed.sort(key=missed_sort_key)
    return [m[0] for m in missed]

def print_missed_task_block(task: Task):
    bar = Fore.YELLOW + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" + Style.RESET_ALL
    header = Fore.YELLOW + "⚠  Mission window missed" + Style.RESET_ALL
    print(bar)
    print(header)
    print(bar)
    
    title_val = Fore.WHITE + Style.BRIGHT + task.title + Style.RESET_ALL
    print(f"Task:     {title_val}")
    
    dl_dt = datetime.fromisoformat(task.deadline)
    if dl_dt.tzinfo is not None:
        dt = dl_dt.replace(tzinfo=None)
    else:
        dt = dl_dt
    due_val = dt.strftime('%A, %b %d at %H:%M')
    
    is_hard = (getattr(task, 'deadline_type', None) == "hard")
    due_color = Fore.RED if is_hard else Fore.YELLOW
    print(f"Was due:  {due_color}{due_val}{Style.RESET_ALL}")
    
    dur_val = task.duration if task.duration else "not set"
    print(f"Priority: {task.priority}  ·  Duration: {dur_val}")
    
    if task.postpone_count >= 1:
        postpone_color = Fore.YELLOW if task.postpone_count < 5 else Fore.RED
        print(f"Postponed: {postpone_color}{task.postpone_count}×{Style.RESET_ALL}")
        
    print(bar)
    print()
    print("What do you want to do?")
    print()
    print("  [E]  Execute now     — mark as active, start tracking")
    print("  [P]  Postpone        — reschedule to a new time")
    print("  [D]  Drop            — remove from active tasks")
    print("  [O]  Offload         — not my responsibility")
    print("  [S]  Skip for now    — decide this later")
    print("  [Q]  Quit review     — return to your list")
    print()

def postpone_flow(task: Task, tasks: List[Task], original_deadline: datetime, today_str: str, triggered_by: str = "missed_flow") -> bool:
    count = task.postpone_count
    if count == 2:
        print(Fore.YELLOW + "⚠  Heads up: you've postponed this twice already." + Style.RESET_ALL)
    elif count in [3, 4]:
        print(Fore.YELLOW + f"""┌─────────────────────────────────────────┐
│  ⚠  Postponed {count} times.               │
│  This task keeps getting pushed back.   │
│  Is it actually going to happen?        │
└─────────────────────────────────────────┘""" + Style.RESET_ALL)
        
    print(f"\nReschedule \"{task.title}\" to:")
    print("[1]  +30 minutes")
    print("[2]  +1 hour")
    print("[3]  +2 hours")
    print("[4]  Tomorrow, same time")
    if count in [3, 4]:
        print("[5]  Custom (type a new deadline)")
        print("[6]  Drop instead\n")
    else:
        print("[5]  Custom (type a new deadline)\n")
        
    p_choice = get_valid_input("Choice [1]: ", "1").strip()
    now = datetime.now()
    
    if count in [3, 4] and p_choice == "6":
        task.status = "dropped"
        task.dropped_at = now.isoformat()
        task.drop_reason = "user decision — missed deadline"
        task.last_decision = "D"
        task.last_decision_at = now.isoformat()
        task.last_missed_prompt = today_str
        storage.save_tasks(tasks)
        print(Fore.WHITE + Style.DIM + "Task dropped. It's done with." + Style.RESET_ALL)
        
        hours_overdue = (now - original_deadline).total_seconds() / 3600.0
        log_behavior({
            "event": "missed_task_decision",
            "task_id": task.id,
            "decision": "D",
            "postpone_count": task.postpone_count,
            "deadline_type": getattr(task, 'deadline_type', 'soft'),
            "hours_overdue": round(hours_overdue, 2)
        })
        return True
        
    new_dt = None
    if p_choice == "1":
        new_dt = now + timedelta(minutes=30)
    elif p_choice == "2":
        new_dt = now + timedelta(hours=1)
    elif p_choice == "3":
        new_dt = now + timedelta(hours=2)
    elif p_choice == "4":
        new_dt = original_deadline + timedelta(days=1)
    elif p_choice == "5":
        while True:
            custom_input = get_valid_input("New deadline (e.g. tomorrow 3pm): ").strip()
            if not custom_input:
                break
            parsed = parse_deadline(custom_input)
            if parsed:
                print(f"→ Deadline set: {parsed.strftime('%A, %d %b %Y at %H:%M')}")
                confirm = get_valid_input("Confirm? [Y/n]: ", "y").lower()
                if confirm == "y" or confirm == "":
                    new_dt = parsed
                    break
            else:
                print("Could not understand. Try: \"tomorrow 3pm\" or \"Friday\"")
                
    if new_dt:
        task.deadline = new_dt.isoformat()
        task.postpone_count += 1
        task.postpone_history.append(now.isoformat())
        
        ph = task.postpone_history
        if len(ph) >= 2:
            gaps = []
            for i in range(1, len(ph)):
                t1 = datetime.fromisoformat(ph[i-1])
                t2 = datetime.fromisoformat(ph[i])
                gaps.append((t2-t1).total_seconds() / 3600.0)
            task.average_postpone_gap_hours = round(sum(gaps)/len(gaps), 1)
            task.postpone_velocity = task.average_postpone_gap_hours

        task.last_decision = "P"
        task.last_decision_at = now.isoformat()
        task.last_missed_prompt = today_str
        calculate_reminder_time(task)
        task.reminder_fired = False
        task.reminder_fired_2 = False
        task.reminder_dismissed = False
        storage.save_tasks(tasks)
        
        print(f"Rescheduled to {new_dt.strftime('%A, %d %b at %I:%M %p')}.")
        new_count = task.postpone_count
        if new_count >= 2:
            msg = f"Postponed {new_count} time(s) total."
            print((Fore.RED if new_count >= 5 else Fore.YELLOW) + msg + Style.RESET_ALL)
            
        hours_overdue = (now - original_deadline).total_seconds() / 3600.0
        log_behavior({
            "event": "missed_task_decision",
            "task_id": task.id,
            "decision": "P",
            "postpone_count": task.postpone_count,
            "deadline_type": getattr(task, 'deadline_type', 'soft'),
            "hours_overdue": round(hours_overdue, 2)
        })
        log_behavior({
            "event": "task_postponed",
            "task_id": task.id,
            "postpone_count": task.postpone_count,
            "new_deadline": task.deadline,
            "velocity": task.postpone_velocity,
            "triggered_by": triggered_by,
            "gap_from_original_hours": round((new_dt - original_deadline).total_seconds() / 3600.0, 2)
        })
        return True
    else:
        print("Invalid choice. Skipping postpone.")
        return False

def prompt_missed_task(task: Task, tasks: List[Task]) -> bool:
    today_str = datetime.now().strftime('%Y-%m-%d')
    original_deadline = datetime.fromisoformat(task.deadline)
    if original_deadline.tzinfo is not None:
        original_deadline = original_deadline.replace(tzinfo=None)
        
    def get_choice():
        while True:
            print_missed_task_block(task)
            choice = get_valid_input("Choice: ").strip().upper()
            if choice in ['E', 'P', 'D', 'O', 'S', 'Q']:
                return choice
            print("Please enter E, P, D, O, S (skip), or Q (quit).")

    choice = get_choice()
    if choice == 'Q':
        return 'quit'        # do NOT set last_missed_prompt — stays for next time
    if choice == 'S' or choice is None:
        return 'skipped'     # do NOT set last_missed_prompt — reappears next time
        
    if choice == 'P' and task.postpone_count >= 5:
        print(Fore.RED + f"""┌─────────────────────────────────────────┐
│  ⚠  Postponed {task.postpone_count} times.               │
│  This task has never been executed.     │
│  Postpone is no longer available.       │
└─────────────────────────────────────────┘""" + Style.RESET_ALL)
        while True:
            print("\nOptions:")
            print("  [E]  Execute now — just do it")
            print("  [D]  Drop it — it's not happening")
            print("  [O]  Offload — not your responsibility\n")
            sub_choice = get_valid_input("Choice: ").strip().upper()
            if sub_choice == 'P':
                print(Fore.RED + f"You've postponed this {task.postpone_count} times.\nThat option is no longer available." + Style.RESET_ALL)
            elif sub_choice in ['E', 'D', 'O']:
                choice = sub_choice
                break
            else:
                print("Please enter E, D, or O.")
                
    if choice == 'E':
        task.status = "active"
        task.executed_late = True
        task.actual_start_time = datetime.now().isoformat()
        task.last_decision = "E"
        task.last_decision_at = datetime.now().isoformat()
        task.last_missed_prompt = today_str
        storage.save_tasks(tasks)
        print(Fore.GREEN + Style.BRIGHT + "Execution started. Focus up." + Style.RESET_ALL)
        
        hours_overdue = (datetime.now() - original_deadline).total_seconds() / 3600.0
        log_behavior({
            "event": "missed_task_decision",
            "task_id": task.id,
            "decision": "E",
            "postpone_count": task.postpone_count,
            "deadline_type": getattr(task, 'deadline_type', 'soft'),
            "hours_overdue": round(hours_overdue, 2)
        })
        return 'decided'
        
    elif choice == 'D':
        task.status = "dropped"
        task.dropped_at = datetime.now().isoformat()
        task.drop_reason = "user decision — missed deadline"
        task.last_decision = "D"
        task.last_decision_at = datetime.now().isoformat()
        task.last_missed_prompt = today_str
        storage.save_tasks(tasks)
        print(Fore.WHITE + Style.DIM + "Task dropped. It's done with." + Style.RESET_ALL)

        hours_overdue = (datetime.now() - original_deadline).total_seconds() / 3600.0
        log_behavior({
            "event": "missed_task_decision",
            "task_id": task.id,
            "decision": "D",
            "postpone_count": task.postpone_count,
            "deadline_type": getattr(task, 'deadline_type', 'soft'),
            "hours_overdue": round(hours_overdue, 2)
        })
        return 'decided'
        
    elif choice == 'O':
        task.status = "offloaded"
        task.offloaded_at = datetime.now().isoformat()
        task.last_decision = "O"
        task.last_decision_at = datetime.now().isoformat()
        task.last_missed_prompt = today_str
        note = get_valid_input("Brief note (who/why) [optional]: ").strip()
        task.offload_note = note
        storage.save_tasks(tasks)
        print(Fore.WHITE + Style.DIM + "Noted. Responsibility transferred." + Style.RESET_ALL)

        hours_overdue = (datetime.now() - original_deadline).total_seconds() / 3600.0
        log_behavior({
            "event": "missed_task_decision",
            "task_id": task.id,
            "decision": "O",
            "postpone_count": task.postpone_count,
            "deadline_type": getattr(task, 'deadline_type', 'soft'),
            "hours_overdue": round(hours_overdue, 2)
        })
        return 'decided'
        
    elif choice == 'P':
        return 'decided' if postpone_flow(task, tasks, original_deadline, today_str) else 'skipped'

def handle_missed_tasks():
    """Show alerts for missed deadlines."""
    try:
        tasks = storage.load_tasks()
    except Exception:
        return
        
    missed = get_missed_tasks(tasks)
    if not missed:
        return
        
    print(Fore.YELLOW + f"You have {len(missed)} missed mission(s) to address." + Style.RESET_ALL)
    print()
    
    for task in missed:
        prompt_missed_task(task, tasks)

    print()


def _print_missed_list_row(task: Task) -> None:
    """One plain row for 'taskflow missed --skip' (no prompts)."""
    due = ""
    try:
        dt = datetime.fromisoformat(task.deadline)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        if getattr(task, 'deadline_type', None) == 'hard':
            due = dt.strftime('%b %d at %H:%M').replace(' 0', ' ')
        else:
            due = dt.strftime('%b %d').replace(' 0', ' ')
    except Exception:
        due = task.deadline or ""
    title = task.title if len(task.title) <= 34 else task.title[:33] + "…"
    print(f"  · #{task.id:<4} {title:<36} Was due: {due}")


def command_missed(hard_only: bool = False, soft_only: bool = False, skip_list: bool = False) -> None:
    """Dedicated, user-invoked review of missed missions.

    This is the ONLY place the interactive Execute/Postpone/Drop/Offload flow
    runs. It is never triggered automatically by list/today. Always escapable
    via [S] Skip and [Q] Quit.
    """
    R = Style.RESET_ALL
    tasks = storage.load_tasks()
    hard, soft = _split_missed(tasks)
    if hard_only:
        missed = list(hard)
    elif soft_only:
        missed = list(soft)
    else:
        missed = list(hard) + list(soft)  # hard first

    if not missed:
        print(Fore.GREEN + "No missed missions. You're on track." + R)
        return

    # --skip : plain, non-interactive listing
    if skip_list:
        print(f"\nMissed missions ({len(missed)} total):\n")
        if hard and not soft_only:
            print(Fore.RED + Style.BRIGHT + "HARD DEADLINE:" + R)
            for t in hard:
                _print_missed_list_row(t)
            print()
        if soft and not hard_only:
            print(Fore.YELLOW + "SOFT DEADLINE:" + R)
            for t in soft:
                _print_missed_list_row(t)
            print()
        print(Fore.WHITE + Style.DIM + "Run: taskflow missed  to address them." + R)
        return

    # Interactive review (escapable)
    bar = Fore.YELLOW + "━" * 38 + R
    print(bar)
    print(Fore.YELLOW + "⚡  Missed Mission Review" + R)
    print(bar)
    print(Fore.YELLOW + f"You have {len(missed)} missed mission(s)." + R)
    print(Fore.YELLOW + "Address them one by one, or press S to skip any." + R)
    print(Fore.YELLOW + "Press Q at any time to quit and return to list." + R)
    print(bar)
    print()

    addressed = skipped = 0
    quit_early = False
    for task in missed:
        # reload so each decision persists and is seen by the next iteration
        tasks = storage.load_tasks()
        live = next((t for t in tasks if t.id == task.id), None)
        if not live:
            continue
        result = prompt_missed_task(live, tasks)
        if result == 'quit':
            quit_early = True
            break
        elif result == 'skipped':
            skipped += 1
            print(Fore.WHITE + Style.DIM + "Skipped. You'll see this again next time." + R)
        else:
            addressed += 1
        print()

    remaining = len(missed) - addressed - skipped
    if quit_early:
        print(Fore.WHITE + Style.DIM + f"Review paused. {remaining} mission(s) still unaddressed." + R)
        print(Fore.WHITE + Style.DIM + "Run: taskflow missed  to continue." + R)
        return

    print(bar)
    print("Review complete.")
    print(f"Addressed: {addressed} · Skipped: {skipped} · Remaining: {remaining}")
    print(bar)


def command_postpone(task_id: int) -> bool:
    """Direct proactive postpone for any task."""
    tasks = storage.load_tasks()
    task = next((t for t in tasks if t.id == task_id), None)
    
    if not task:
        Messenger.task_not_found(task_id)
        return False
        
    if task.completed or getattr(task, 'dropped_at', None) or getattr(task, 'offloaded_at', None):
        status = "completed" if task.completed else ("dropped" if task.dropped_at else "offloaded")
        print(f"Task #{task_id} is {status}. Cannot postpone.")
        return False
        
    if not getattr(task, 'deadline', None):
        print(f"Task #{task_id} has no deadline set.\nAdd one: taskflow edit {task_id}")
        return False
        
    original_deadline = datetime.fromisoformat(task.deadline)
    if original_deadline.tzinfo is not None:
        original_deadline = original_deadline.replace(tzinfo=None)
        
    today_str = datetime.now().strftime('%Y-%m-%d')
    count = task.postpone_count
    
    if count >= 5:
        print(Fore.RED + f"""┌─────────────────────────────────────────┐
│  ⚠  Postponed {count} times.               │
│  This task has never been executed.     │
│  Postpone is no longer available.       │
└─────────────────────────────────────────┘""" + Style.RESET_ALL)
        while True:
            print("\nOptions:")
            print("  [E]  Execute now — just do it")
            print("  [D]  Drop it — it's not happening")
            print("  [O]  Offload — not your responsibility\n")
            sub_choice = get_valid_input("Choice: ").strip().upper()
            if sub_choice == 'P':
                print(Fore.RED + f"You've postponed this {count} times.\nThat option is no longer available." + Style.RESET_ALL)
            elif sub_choice in ['E', 'D', 'O']:
                choice = sub_choice
                break
            else:
                print("Please enter E, D, or O.")
                
        if choice == 'E':
            task.status = "active"
            task.executed_late = True
            task.actual_start_time = datetime.now().isoformat()
            task.last_decision = "E"
            task.last_decision_at = datetime.now().isoformat()
            task.last_missed_prompt = today_str
            storage.save_tasks(tasks)
            print(Fore.GREEN + Style.BRIGHT + "Execution started. Focus up." + Style.RESET_ALL)
            hours_overdue = (datetime.now() - original_deadline).total_seconds() / 3600.0
            log_behavior({
                "event": "missed_task_decision",
                "task_id": task.id,
                "decision": "E",
                "postpone_count": task.postpone_count,
                "deadline_type": getattr(task, 'deadline_type', 'soft'),
                "hours_overdue": round(hours_overdue, 2)
            })
            return True
        elif choice == 'D':
            task.status = "dropped"
            task.dropped_at = datetime.now().isoformat()
            task.drop_reason = "user decision — missed deadline"
            task.last_decision = "D"
            task.last_decision_at = datetime.now().isoformat()
            task.last_missed_prompt = today_str
            storage.save_tasks(tasks)
            print(Fore.WHITE + Style.DIM + "Task dropped. It's done with." + Style.RESET_ALL)
            hours_overdue = (datetime.now() - original_deadline).total_seconds() / 3600.0
            log_behavior({
                "event": "missed_task_decision",
                "task_id": task.id,
                "decision": "D",
                "postpone_count": task.postpone_count,
                "deadline_type": getattr(task, 'deadline_type', 'soft'),
                "hours_overdue": round(hours_overdue, 2)
            })
            return True
        elif choice == 'O':
            task.status = "offloaded"
            task.offloaded_at = datetime.now().isoformat()
            task.last_decision = "O"
            task.last_decision_at = datetime.now().isoformat()
            task.last_missed_prompt = today_str
            note = get_valid_input("Brief note (who/why) [optional]: ").strip()
            task.offload_note = note
            storage.save_tasks(tasks)
            print(Fore.WHITE + Style.DIM + "Noted. Responsibility transferred." + Style.RESET_ALL)
            hours_overdue = (datetime.now() - original_deadline).total_seconds() / 3600.0
            log_behavior({
                "event": "missed_task_decision",
                "task_id": task.id,
                "decision": "O",
                "postpone_count": task.postpone_count,
                "deadline_type": getattr(task, 'deadline_type', 'soft'),
                "hours_overdue": round(hours_overdue, 2)
            })
            return True
    else:
        return postpone_flow(task, tasks, original_deadline, today_str, triggered_by="postpone_cmd")



def calculate_reminder_time(task) -> Optional[datetime]:
    """Calculate the ideal reminder time for a task based on rules."""
    if not task.deadline:
        return None
        
    try:
        dt = datetime.fromisoformat(task.deadline)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
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
        fired_second = False
        try:
            r1 = datetime.fromisoformat(task.reminder_time)
            if r1.tzinfo is not None:
                r1 = r1.replace(tzinfo=None)
            if now >= r1 and not task.reminder_fired:
                is_due = True
                task.reminder_fired = True
        except ValueError:
            pass

        if not is_due and task.reminder_time_2:
            try:
                r2 = datetime.fromisoformat(task.reminder_time_2)
                if r2.tzinfo is not None:
                    r2 = r2.replace(tzinfo=None)
                if now >= r2 and not task.reminder_fired_2:
                    is_due = True
                    fired_second = True
                    task.reminder_fired_2 = True
            except ValueError:
                pass

        if is_due:
            due.append(task)
            try:
                _ddt = datetime.fromisoformat(task.deadline)
                if _ddt.tzinfo is not None:
                    _ddt = _ddt.replace(tzinfo=None)
                _hrs = round((_ddt - now).total_seconds() / 3600.0, 1)
            except Exception:
                _hrs = None
            log_behavior({
                "event": "reminder_fired",
                "task_id": task.id,
                "is_second": fired_second,
                "hours_before_deadline": _hrs,
                "deadline_type": getattr(task, 'deadline_type', 'soft')
            })
            
    if due:
        storage.save_tasks(tasks)
        if len(due) >= 3:
            print(Fore.YELLOW + f"You have {len(due)} reminders firing at once. Showing one at a time." + Style.RESET_ALL)
            
        for task in due:
            show_t = datetime.now()
            try:
                dt = datetime.fromisoformat(task.deadline)
                now = datetime.now()
                today = now.replace(hour=0, minute=0, second=0, microsecond=0)
                task_date = dt.replace(hour=0, minute=0, second=0, microsecond=0)
                
                if dt < now:
                    # D4-03: never quantify lateness in crushing minutes — calm word or date
                    if (now - dt).total_seconds() > 86400:
                        due_str = "overdue · was due " + dt.strftime('%b %d').replace(' 0', ' ')
                    else:
                        due_str = "overdue"
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
  ║  Priority: {task.priority:<6}  ·  Duration: {str(task.duration or '—'):<12}║{hard_line}
  ╚══════════════════════════════════════════════╝""" + Style.RESET_ALL)
            
            # D4-01: reminders NEVER block startup (taskflow list/today must not trap the user).
            # Shown once (reminder_fired persists above), then out of the way. Dismiss via
            # `taskflow remind` / the web UI; start via `taskflow focus --id`.
            print(f"  {Style.DIM}Start: taskflow focus --id {task.id}  ·  dismiss: taskflow remind {task.id} --clear{Style.RESET_ALL}\n")
            choice = ""
            _delay = round((datetime.now() - show_t).total_seconds())

            if choice == "D":
                task.reminder_dismissed = True
                task.reminder_response = "dismissed"
                print(Fore.WHITE + Style.DIM + "Reminder dismissed. Won't show again." + Style.RESET_ALL)
            elif choice == "S":
                task.reminder_response = "started_focus"
                task.actual_start_time = datetime.now().isoformat()
                try:
                    _rt = datetime.fromisoformat(task.reminder_time)
                    if _rt.tzinfo is not None:
                        _rt = _rt.replace(tzinfo=None)
                    task.reminder_to_action_gap_minutes = round((datetime.now() - _rt).total_seconds() / 60.0, 1)
                except Exception:
                    pass
                print(Fore.CYAN + f"Starting focus on: {task.title}" + Style.RESET_ALL)
                print(Fore.CYAN + f"Run: taskflow focus --id {task.id}" + Style.RESET_ALL)
            else:
                task.reminder_response = "noted"
                print(Fore.CYAN + Style.DIM + "Reminder noted." + Style.RESET_ALL)

            log_behavior({
                "event": "reminder_response",
                "task_id": task.id,
                "response": task.reminder_response,
                "response_delay_seconds": _delay
            })
            storage.save_tasks(tasks)

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

    dismissed = "yes" if getattr(task, 'reminder_dismissed', False) else "no"
    print(f"Dismissed:  {dismissed}")
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

def detect_link_type(val: str) -> str:
    """Auto-detect link/reference type."""
    val_lower = val.lower()
    # Map detection must precede the generic http(s) check, since map URLs
    # also start with https:// and would otherwise always classify as "url".
    if "maps.google" in val_lower or "maps.apple" in val_lower or "goo.gl/maps" in val_lower:
        return "map"
    elif val_lower.startswith("http://") or val_lower.startswith("https://"):
        return "url"
    elif val.startswith("/") or val.startswith("~") or (len(val) >= 3 and val[1:3] == ":\\"):
        return "file"
    else:
        return "reference"

def prompt_description() -> Optional[str]:
    """Prompt user for a description/note with multi-line support."""
    first_line = get_valid_input("> ")
    if not first_line:
        return None
    if first_line.strip() == "...":
        print("Multi-line mode. Type END on its own line to finish.")
        lines = []
        while True:
            line = get_valid_input("")
            if line == "END":
                break
            lines.append(line)
        return "\n".join(lines)
    else:
        return first_line

def edit_note(task_id: int) -> bool:
    """Edit or append notes/description of a task (E5)."""
    tasks = storage.load_tasks()
    task = next((t for t in tasks if t.id == task_id), None)
    if not task:
        Messenger.task_not_found(task_id)
        return False
        
    existing = getattr(task, 'description', None)
    if existing:
        print("Current notes:")
        print("──────────────────────")
        print(existing)
        print("──────────────────────")
        choice = get_valid_input("Edit? [Y/n/append]: ", "y").strip().lower()
        
        if choice in ['y', 'yes']:
            print("Enter new notes (Enter to skip):")
            new_desc = prompt_description()
            task.description = new_desc
            task.description_updated_at = datetime.now().isoformat()
        elif choice in ['append', 'a']:
            print("Enter notes to append:")
            append_desc = prompt_description()
            if append_desc:
                if task.description:
                    task.description += "\n" + append_desc
                else:
                    task.description = append_desc
                task.description_updated_at = datetime.now().isoformat()
        else:
            print("No changes made.")
            return False
    else:
        print("No notes yet.")
        print("Add notes (Enter to skip):")
        new_desc = prompt_description()
        task.description = new_desc
        task.description_updated_at = datetime.now().isoformat()
        
    storage.save_tasks(tasks)
    if task.description:
        print(Fore.GREEN + f"→ Notes updated for task #{task_id}." + Style.RESET_ALL)
    else:
        print(Fore.GREEN + f"→ Notes cleared for task #{task_id}." + Style.RESET_ALL)
    return True

def manage_links(task_id: int, add_url: str = None, title: str = None) -> bool:
    """View and manage links for a task (E6)."""
    tasks = storage.load_tasks()
    task = next((t for t in tasks if t.id == task_id), None)
    if not task:
        Messenger.task_not_found(task_id)
        return False
        
    if not getattr(task, 'links', None):
        task.links = []
        
    # Non-interactive direct command version
    if add_url:
        if len(task.links) >= 10:
            print("Maximum 10 links reached.")
            return False
            
        next_num = 1
        if task.links:
            ids = []
            for l in task.links:
                try:
                    num = int(l.get("id").replace("lnk_", ""))
                    ids.append(num)
                except ValueError:
                    pass
            if ids:
                next_num = max(ids) + 1
                
        link_id = f"lnk_{next_num:03d}"
        l_type = detect_link_type(add_url)
        
        task.links.append({
            "id": link_id,
            "type": l_type,
            "url": add_url,
            "title": title if title else None,
            "added_at": datetime.now().isoformat()
        })
        task.links_count = len(task.links)
        storage.save_tasks(tasks)
        print(Fore.GREEN + f"→ Link {link_id} added." + Style.RESET_ALL)
        return True
        
    # Interactive menu
    while True:
        print(f"\nLinks for task #{task.id} · {task.title}")
        if not task.links:
            print("  No links attached.")
        else:
            for l in task.links:
                lnk_id = l.get("id")
                lnk_type = l.get("type", "url")
                lnk_url = l.get("url")
                lnk_title = l.get("title")
                
                id_str = f"[{lnk_id}]"
                type_str = f"{lnk_type:<10}"
                print(f"  {id_str} {type_str} {lnk_url}")
                if lnk_title:
                    print(f"                      \"{lnk_title}\"")
                    
        print("\n  [A] Add new link")
        print("  [R] Remove a link")
        print("  [O] Open a link (prints URL to copy)")
        print("  [X] Exit")
        choice = get_valid_input("Choice: ").strip().upper()
        
        if choice == 'A':
            if len(task.links) >= 10:
                print("Maximum 10 links reached.")
                continue
            url = get_valid_input("Paste a URL, map location, or reference (Enter to cancel): ").strip()
            if not url:
                continue
            l_type = detect_link_type(url)
            print(f"Detected: {l_type}")
            label = get_valid_input("Label (optional, e.g. \"Design doc\", Enter to skip): ").strip()
            
            next_num = 1
            if task.links:
                ids = []
                for l in task.links:
                    try:
                        num = int(l.get("id").replace("lnk_", ""))
                        ids.append(num)
                    except ValueError:
                        pass
                if ids:
                    next_num = max(ids) + 1
            link_id = f"lnk_{next_num:03d}"
            
            task.links.append({
                "id": link_id,
                "type": l_type,
                "url": url,
                "title": label if label else None,
                "added_at": datetime.now().isoformat()
            })
            task.links_count = len(task.links)
            storage.save_tasks(tasks)
            print(Fore.GREEN + f"→ Link added." + Style.RESET_ALL)
            
        elif choice == 'R':
            if not task.links:
                print("No links to remove.")
                continue
            lnk_id = get_valid_input("Enter link ID to remove (e.g. lnk_001): ").strip()
            link_obj = next((l for l in task.links if l.get("id") == lnk_id), None)
            if not link_obj:
                print("Link ID not found.")
                continue
            title_or_url = link_obj.get("title") or link_obj.get("url")
            confirm = get_valid_input(f"Confirm remove \"{title_or_url}\"? [Y/n]: ", "y").strip().lower()
            if confirm == 'y' or confirm == '':
                task.links.remove(link_obj)
                task.links_count = len(task.links)
                storage.save_tasks(tasks)
                print(Fore.GREEN + "→ Link removed." + Style.RESET_ALL)
                
        elif choice == 'O':
            if not task.links:
                print("No links to open.")
                continue
            lnk_id = get_valid_input("Enter link ID: ").strip()
            link_obj = next((l for l in task.links if l.get("id") == lnk_id), None)
            if not link_obj:
                print("Link ID not found.")
                continue
            url = link_obj.get("url")
            l_type = link_obj.get("type", "url")
            
            print(f"Value: {url}")
            if l_type in ["url", "map"]:
                print("Copy this URL and open in your browser.")
                try:
                    import sys, subprocess, os
                    if sys.platform == 'win32':
                        os.startfile(url)
                    elif sys.platform == 'darwin':
                        subprocess.run(["open", url])
                    else:
                        subprocess.run(["xdg-open", url])
                except Exception:
                    pass
            else:
                if l_type == "file":
                    try:
                        import sys, subprocess, os
                        if sys.platform == 'win32':
                            os.startfile(url)
                        elif sys.platform == 'darwin':
                            subprocess.run(["open", url])
                        else:
                            subprocess.run(["xdg-open", url])
                    except Exception:
                        pass
                        
        elif choice == 'X' or not choice:
            break
    return True

def manage_checklist(task_id: int, toggle_index: int = None) -> bool:
    """View and manage checklist for a task (E7)."""
    tasks = storage.load_tasks()
    task = next((t for t in tasks if t.id == task_id), None)
    if not task:
        Messenger.task_not_found(task_id)
        return False
        
    if not getattr(task, 'checklist', None):
        task.checklist = []
        
    # Direct non-interactive toggle
    if toggle_index is not None:
        idx = toggle_index - 1
        if idx < 0 or idx >= len(task.checklist):
            print(f"Invalid checklist item index: {toggle_index}")
            return False
        item = task.checklist[idx]
        if item.get("done"):
            item["done"] = False
            item["done_at"] = None
            print(Fore.GREEN + f"→ Checklist item {toggle_index} marked incomplete." + Style.RESET_ALL)
        else:
            item["done"] = True
            item["done_at"] = datetime.now().isoformat()
            print(Fore.GREEN + f"→ Checklist item {toggle_index} marked complete." + Style.RESET_ALL)
            
        task.checklist_total = len(task.checklist)
        task.checklist_done = sum(1 for x in task.checklist if x.get("done"))
        storage.save_tasks(tasks)
        return True
        
    # Interactive menu
    while True:
        print(f"\nChecklist for task #{task.id} · {task.title}")
        print("─────────────────────────────────────────────")
        if not task.checklist:
            print("  No checklist items.")
        else:
            for idx, item in enumerate(task.checklist):
                is_done = item.get("done")
                checkmark = "✓" if is_done else "·"
                mark_color = Fore.GREEN if is_done else Fore.WHITE + Style.DIM
                text_color = Fore.WHITE if is_done else Fore.WHITE + Style.DIM
                print(f"  [{idx+1}] {mark_color}{checkmark}{Style.RESET_ALL}  {text_color}{item.get('text')}{Style.RESET_ALL}")
        print("─────────────────────────────────────────────")
        
        done_count = sum(1 for x in task.checklist if x.get("done"))
        total_count = len(task.checklist)
        pct = int(done_count / total_count * 100) if total_count > 0 else 0
        print(f"  Progress: {done_count}/{total_count} done ({pct}%)")
        
        print("\n  Enter item number to toggle, A to add, R to remove, or Enter to exit:")
        choice = get_valid_input("Choice: ").strip()
        
        if not choice:
            break
            
        if choice.upper() == 'A':
            if len(task.checklist) >= 20:
                print("Maximum 20 checklist items reached.")
                continue
            text = get_valid_input("New item text: ").strip()
            if not text:
                continue
                
            next_num = 1
            if task.checklist:
                ids = []
                for x in task.checklist:
                    try:
                        num = int(x.get("id").replace("chk_", ""))
                        ids.append(num)
                    except ValueError:
                        pass
                if ids:
                    next_num = max(ids) + 1
            chk_id = f"chk_{next_num:03d}"
            
            task.checklist.append({
                "id": chk_id,
                "text": text,
                "done": False,
                "done_at": None
            })
            task.checklist_total = len(task.checklist)
            task.checklist_done = sum(1 for x in task.checklist if x.get("done"))
            storage.save_tasks(tasks)
            print(Fore.GREEN + "→ Item added." + Style.RESET_ALL)
            
        elif choice.upper() == 'R':
            if not task.checklist:
                print("No items to remove.")
                continue
            try:
                num = int(get_valid_input("Enter item number to remove: "))
                idx = num - 1
                if 0 <= idx < len(task.checklist):
                    task.checklist.pop(idx)
                    task.checklist_total = len(task.checklist)
                    task.checklist_done = sum(1 for x in task.checklist if x.get("done"))
                    storage.save_tasks(tasks)
                    print(Fore.GREEN + "→ Item removed." + Style.RESET_ALL)
                else:
                    print("Invalid item number.")
            except ValueError:
                print("Please enter a valid number.")
                
        else:
            try:
                num = int(choice)
                idx = num - 1
                if 0 <= idx < len(task.checklist):
                    item = task.checklist[idx]
                    if item.get("done"):
                        item["done"] = False
                        item["done_at"] = None
                        print(Fore.GREEN + f"→ Item {num} marked incomplete." + Style.RESET_ALL)
                    else:
                        item["done"] = True
                        item["done_at"] = datetime.now().isoformat()
                        print(Fore.GREEN + f"→ Item {num} marked complete." + Style.RESET_ALL)
                    task.checklist_total = len(task.checklist)
                    task.checklist_done = sum(1 for x in task.checklist if x.get("done"))
                    storage.save_tasks(tasks)
                else:
                    print("Invalid item number.")
            except ValueError:
                print("Invalid input. Enter a number, A, R, or Enter to exit.")
    return True

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
        priority_input = get_valid_input("Priority — Critical/Strategic/Noise/Purge (High/Medium/Low also accepted) [Strategic]: ", "Medium")
        
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
        duration = normalize_duration(preset_duration)  # D1-01: validate --duration presets too
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
            dl_input = get_valid_input("Deadline (e.g. tomorrow 3pm, Friday, in 2h) [skip]: ")
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
                    dl_input = get_valid_input("Deadline (e.g. tomorrow 3pm, Friday, in 2h) [skip]: ")
                    if not dl_input:
                        break
                    parsed_dl = parse_deadline(dl_input)
                    if parsed_dl:
                        print(f"→ Deadline set: {parsed_dl.strftime('%A, %d %b %Y at %H:%M')}")
                        confirm2 = get_valid_input("Confirm? [Y/n]: ", "y").lower()
                        if confirm2 == "y" or confirm2 == "":
                            deadline_iso = parsed_dl.isoformat()
                    break
            else:
                print("Could not understand. Try: \"tomorrow 3pm\" or \"Friday\"")
                dl_input = get_valid_input("Deadline (e.g. tomorrow 3pm, Friday, in 2h) [skip]: ")
                if not dl_input:
                    break
                parsed_dl = parse_deadline(dl_input)
                if parsed_dl:
                    print(f"→ Deadline set: {parsed_dl.strftime('%A, %d %b %Y at %H:%M')}")
                    confirm2 = get_valid_input("Confirm? [Y/n]: ", "y").lower()
                    if confirm2 == "y" or confirm2 == "":
                        deadline_iso = parsed_dl.isoformat()
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

    # E2 - PROMPT 1: Description
    print()
    print("Notes (optional, Enter to skip):")
    description = prompt_description()
    description_updated_at = datetime.now().isoformat() if description else None
    
    # E2 - PROMPT 2: Links
    links = []
    print()
    first_url = get_valid_input("Paste a URL, map location, or reference (Enter to skip): ").strip()
    if first_url:
        while True:
            l_type = detect_link_type(first_url)
            print(f"Detected: {l_type}")
            label = get_valid_input("Label (optional, e.g. \"Design doc\", Enter to skip): ").strip()
            
            link_id = f"lnk_{len(links)+1:03d}"
            links.append({
                "id": link_id,
                "type": l_type,
                "url": first_url,
                "title": label if label else None,
                "added_at": datetime.now().isoformat()
            })
            
            if len(links) >= 10:
                print("Maximum 10 links reached.")
                break
                
            another = get_valid_input("Add another link? [y/N]: ", "n").strip().lower()
            if another == 'y' or another == 'yes':
                first_url = get_valid_input("Paste a URL, map location, or reference (Enter to skip): ").strip()
                if not first_url:
                    break
            else:
                break
                
    # E2 - PROMPT 3: Checklist
    checklist = []
    print()
    add_chk = get_valid_input("Add checklist items? [y/N]: ", "n").strip().lower()
    if add_chk == 'y' or add_chk == 'yes':
        print("Add items one by one. Enter blank line when done.")
        while len(checklist) < 20:
            item_text = get_valid_input(f"Item [{len(checklist)+1}]: ").strip()
            if not item_text:
                break
            chk_id = f"chk_{len(checklist)+1:03d}"
            checklist.append({
                "id": chk_id,
                "text": item_text,
                "done": False,
                "done_at": None
            })

    task = Task(
        id=0,  # Will be auto-assigned
        title=title,
        priority=priority,
        tags=tags
    )
    task.duration = duration
    task.deadline = deadline_iso
    task.deadline_type = deadline_type
    
    # Enrichment fields
    task.description = description
    task.links = links
    task.checklist = checklist
    task.description_updated_at = description_updated_at
    task.links_count = len(links)
    task.checklist_total = len(checklist)
    task.checklist_done = 0
    
    if deadline_iso:
        task.deadline_raw = dl_input if not preset_deadline else preset_deadline
        try:
            dl_dt = datetime.fromisoformat(deadline_iso)
            task.deadline_set_advance_hours = round((dl_dt - datetime.now()).total_seconds() / 3600, 1)
        except Exception:
            pass
    
    if deadline_iso:
        calculate_reminder_time(task)
        
    try:
        task_id = manager.add_task(task)
        storage.save_tasks(manager.tasks)
        
        # E2 custom success message
        desc_notes = " · notes added" if task.description else ""
        link_str = ""
        if task.links:
            count = len(task.links)
            if task.description:
                link_str = f" · {count} links"
            else:
                link_str = f" · {count} links attached"
        chk_str = f" · {len(task.checklist)} checklist items" if task.checklist else ""
        
        if desc_notes or link_str or chk_str:
            dur_part = f". Est. {duration}" if duration else ""
            print(f"→ Task #{task_id} added{dur_part}{desc_notes}{link_str}{chk_str}.")
        else:
            if duration:
                print(f"→ Task #{task_id} added. Est. {duration}.")
            else:
                print(f"→ Task #{task_id} added successfully.")
        return True
    except Exception as e:
        Messenger.careful(f"Could not add task: {e}")
        return False

def dump_task(title: str, duration: str = None, deadline: str = None, is_hard: bool = False, note: str = None, links: list = None) -> dict:
    """Frictionless capture: instantly add a task without prompts.

    note  : optional description string (E3 --note).
    links : optional list of {"url": str, "title": str|None} dicts (E3 --link/--link-title).
    """
    import re
    from datetime import datetime
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

    # S2-D: extract an inline natural-language deadline from the text (when no --deadline flag)
    inline_deadline_dt = None
    inline_phrase = None
    if not deadline:
        _date_pat = re.compile(
            r'\b('
            r'tomorrow(?:\s+(?:morning|afternoon|evening|night))?(?:\s+at)?(?:\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?'
            r'|today(?:\s+at)?(?:\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?|tonight'
            r'|this\s+(?:morning|afternoon|evening)'
            r'|next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
            r'|(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)(?:\s+at)?(?:\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?'
            r'|in\s+\d+\s*(?:minutes?|mins?|hours?|hrs?|days?)'
            r'|\d{1,2}(?::\d{2})?\s*(?:am|pm)'
            r'|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}'
            r')\b',
            re.IGNORECASE
        )
        _m = _date_pat.search(clean_title)
        if _m:
            _parsed = parse_deadline(_m.group(0))
            if _parsed:
                inline_deadline_dt = _parsed
                inline_phrase = _m.group(0).strip()
                clean_title = (clean_title[:_m.start()] + clean_title[_m.end():])
                clean_title = re.sub(r'\s+', ' ', clean_title).strip()

    clean_title = validate_title(clean_title)
    
    if not clean_title:
        return None
        
    task = Task(
        id=0,
        title=clean_title,
        priority=normalize_priority(priority.capitalize()),
        tags=tags
    )
    
    task.duration = normalize_duration(duration)  # D1-01: bucket free text → valid enum (or None)

    if deadline:
        parsed_dl = parse_deadline(deadline)
        if parsed_dl:
            task.deadline = parsed_dl.isoformat()
            task.deadline_raw = deadline
            task.deadline_type = "hard" if is_hard else "soft"
            try:
                task.deadline_set_advance_hours = round((parsed_dl - datetime.now()).total_seconds() / 3600, 1)
            except Exception:
                pass
            calculate_reminder_time(task)
    elif inline_deadline_dt:
        task.deadline = inline_deadline_dt.isoformat()
        task.deadline_raw = inline_phrase
        task.deadline_type = "hard" if is_hard else "soft"
        try:
            task.deadline_set_advance_hours = round((inline_deadline_dt - datetime.now()).total_seconds() / 3600, 1)
        except Exception:
            pass
        calculate_reminder_time(task)

    # E3: enrichment captured via flags
    if note:
        task.description = note
        task.description_updated_at = datetime.now().isoformat()
    if links:
        assembled = []
        for ln in links[:10]:
            url = (ln.get("url") or "").strip()
            if not url:
                continue
            assembled.append({
                "id": f"lnk_{len(assembled)+1:03d}",
                "type": detect_link_type(url),
                "url": url,
                "title": (ln.get("title") or None),
                "added_at": datetime.now().isoformat()
            })
        task.links = assembled
        task.links_count = len(assembled)

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

    print("⚡ Deploying Mission Control...")
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
        print(f"🌊 Mission Control HUD live → {url}")
    except Exception as e:
        print(f"❌ Failed to reach Mission Control: {e}")


def format_time_remaining(td: timedelta, deadline_dt=None) -> str:
    """Format a timedelta for pressure warnings.

    Fix 4: if overdue by more than 24h, NEVER show hours — show the due DATE
    (when `deadline_dt` is provided) or a day count fallback. Big hour numbers
    ("OVERDUE 865h") quantify failure in a crushing unit; a date is just a fact.
    """
    secs = td.total_seconds()
    if secs < 0:
        total = abs(secs)
        if total > 86400:  # overdue by more than a day
            if deadline_dt is not None:
                return f"OVERDUE — {deadline_dt.strftime('%b %d').replace(' 0', ' ')}"
            return f"OVERDUE {int(total // 86400)}d"
        if total > 3600:
            h = int(total // 3600)
            m = int((total % 3600) // 60)
            return f"OVERDUE {h}h {m}m" if m else f"OVERDUE {h}h"
        return f"OVERDUE {int(total // 60)}m"

    if secs > 3600:
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        return f"{h}h {m}m left"
    elif secs >= 60:
        return f"{int(secs // 60)}m left"
    else:
        return f"{int(secs)}s left"


def get_pressure_level(task) -> int:
    """Calculate the pressure level based on deadline proximity."""
    if not getattr(task, 'deadline', None):
        return 0
    if task.completed or getattr(task, 'dropped_at', None) or getattr(task, 'offloaded_at', None):
        return 0
    if getattr(task, 'status', None) in ['completed', 'done', 'dropped', 'offloaded']:
        return 0
        
    try:
        dt = datetime.fromisoformat(task.deadline)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
    except ValueError:
        return 0
        
    td = dt - datetime.now()
    seconds = td.total_seconds()
    
    if seconds > 10800:
        return 0
    elif seconds > 3600:
        return 1
    elif seconds > 900:
        return 2
    else:
        return 3


def _split_missed(tasks: List[Task]):
    """Return (hard_missed, soft_missed) lists of currently-missed pending tasks.

    Uses get_missed_tasks() so tasks already addressed via 'taskflow missed'
    (last_missed_prompt == today) correctly drop off the notices.
    """
    missed = get_missed_tasks(tasks)
    hard = [t for t in missed if getattr(t, 'deadline_type', None) == 'hard']
    soft = [t for t in missed if getattr(t, 'deadline_type', None) != 'hard']
    return hard, soft


def print_list_missed_banner(tasks: List[Task]) -> None:
    """PASSIVE top-of-list notice for missed HARD deadlines. One block, never prompts."""
    hard, _ = _split_missed(tasks)
    if not hard:
        return
    n = len(hard)
    R = Style.RESET_ALL
    red = Fore.RED + Style.BRIGHT
    dim = Fore.WHITE + Style.DIM
    plural = "s" if n != 1 else ""
    line1 = f"⚠  {n} hard deadline{plural} missed"
    line2 = "Run: taskflow missed  to address them"
    W = max(len(line1), len(line2))
    bar = "─" * (W + 2)
    print(dim + "┌" + bar + "┐" + R)
    print(dim + "│ " + R + red + line1.ljust(W) + R + dim + " │" + R)
    print(dim + "│ " + line2.ljust(W) + " │" + R)
    print(dim + "└" + bar + "┘" + R)
    print()


def print_list_missed_footer(tasks: List[Task]) -> None:
    """PASSIVE bottom-of-list notice for missed SOFT deadlines. One line, never prompts."""
    _, soft = _split_missed(tasks)
    if not soft:
        return
    n = len(soft)
    plural = "s" if n != 1 else ""
    R = Style.RESET_ALL
    print(f"\n{Fore.YELLOW}ℹ  {n} soft deadline{plural} passed{R}")
    print(f"{Fore.YELLOW}   Run: taskflow missed --soft  to review{R}")


def print_today_missed_notice(tasks: List[Task]) -> None:
    """PASSIVE bottom-of-today notice for any missed missions. Never prompts."""
    hard, soft = _split_missed(tasks)
    n = len(hard) + len(soft)
    if n == 0:
        return
    R = Style.RESET_ALL
    dim = Fore.WHITE + Style.DIM
    plural = "s" if n != 1 else ""
    print(dim + "─" * 50 + R)
    print(f"{Fore.YELLOW}⚠  {n} missed mission{plural} need attention.{R}")
    print(f"{dim}   Run: taskflow missed  to address them now.{R}")
    print(dim + "─" * 50 + R)


def _list_deadline_dt(t):
    """Parsed naive deadline datetime, or None."""
    if not getattr(t, 'deadline', None):
        return None
    try:
        dt = datetime.fromisoformat(t.deadline)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    except Exception:
        return None


def _enrichment_indicators(t) -> str:
    """`📝 · 🔗 ×N · ☑ N/N` (ascii fallback if stdout can't render emoji)."""
    supports_emoji = False
    try:
        enc = (sys.stdout.encoding or 'ascii').lower()
        supports_emoji = ('utf' in enc or 'cp65001' in enc)
    except Exception:
        pass
    parts = []
    if getattr(t, 'description', None):
        parts.append("📝" if supports_emoji else "[note]")
    if getattr(t, 'links', None):
        parts.append(f"🔗 ×{len(t.links)}" if supports_emoji else f"[{len(t.links)} links]")
    if getattr(t, 'checklist', None):
        done = sum(1 for x in t.checklist if x.get('done'))
        parts.append(f"☑ {done}/{len(t.checklist)}" if supports_emoji else f"[{done}/{len(t.checklist)}]")
    return " · ".join(parts)


def _list_group_header(title, count, color):
    bar = "━" * 38
    plural = "task" if count == 1 else "tasks"
    print(color + bar + Style.RESET_ALL)
    print(color + f"  {title}  ({count} {plural})" + Style.RESET_ALL)
    print(color + bar + Style.RESET_ALL)


def _list_priority_color(t):
    p = (t.priority or "").lower()
    if p in ("critical", "high"):
        return Fore.RED
    if p in ("strategic", "medium"):
        return Fore.CYAN
    if p in ("noise", "low", "purge"):
        return Fore.WHITE + Style.DIM
    return Fore.WHITE


def _print_list_active_task(t, now, show_detail=False):
    pressure = get_pressure_level(t)
    title_color = Fore.WHITE
    if pressure == 3:
        title_color = Fore.RED + Style.BRIGHT
    elif pressure == 2:
        title_color = Fore.YELLOW + Style.BRIGHT

    dur = f"  {Fore.CYAN}[{t.duration}]{Style.RESET_ALL}" if t.duration else ""
    tags = f" · {Fore.BLUE}#{', #'.join(t.tags)}{Style.RESET_ALL}" if t.tags else ""
    pc = t.postpone_count or 0
    postpone = ""
    if pc >= 5:
        postpone = f"  {Fore.RED}(postponed ×{pc}) ⚠⚠{Style.RESET_ALL}"
    elif pc >= 3:
        postpone = f"  {Fore.YELLOW}(postponed ×{pc}) ⚠{Style.RESET_ALL}"
    elif pc == 2:
        postpone = f"  {Fore.YELLOW}(postponed ×2){Style.RESET_ALL}"

    id_str = f"{Fore.GREEN}#{t.id}{Style.RESET_ALL}"
    p_color = _list_priority_color(t)
    print(f"{Fore.WHITE}○{Style.RESET_ALL} {id_str} · {title_color}{t.title}{Style.RESET_ALL}{dur} · {p_color}{t.priority}{Style.RESET_ALL}{tags}{postpone}")

    dt = _list_deadline_dt(t)
    if dt is not None:
        deadline_disp = format_deadline_display(t)  # colored; overdue→date via Fix 4
        suffix = ""
        if pressure >= 1:
            td = dt - now
            if td.total_seconds() >= 0:
                suffix = f" · {format_time_remaining(td, dt)}"
        print(f"       {deadline_disp}{suffix}")

    ind = _enrichment_indicators(t)
    if ind:
        print(f"       {Style.DIM}{ind}{Style.RESET_ALL}")

    if show_detail:
        if getattr(t, 'description', None):
            preview = t.description.replace('\n', ' ')
            if len(preview) > 80:
                preview = preview[:77] + "..."
            print(f"       {Style.DIM}Notes: {preview}{Style.RESET_ALL}")
        for l in (getattr(t, 'links', None) or []):
            tp = f" (\"{l.get('title')}\")" if l.get('title') else ""
            print(f"       {Style.DIM}Link: [{l.get('id')}] {l.get('type')} → {l.get('url')}{tp}{Style.RESET_ALL}")
        for idx, item in enumerate(getattr(t, 'checklist', None) or []):
            chk = "✓" if item.get('done') else "·"
            print(f"       {Style.DIM}Subtask {idx+1}: [{chk}] {item.get('text')}{Style.RESET_ALL}")


def _print_list_done_task(t):
    dur = f"  {Style.DIM}[{t.duration}]{Style.RESET_ALL}" if t.duration else ""
    tags = f" · #{', #'.join(t.tags)}" if t.tags else ""
    print(f"{Fore.GREEN}✓{Style.RESET_ALL} {Style.DIM}#{t.id} · {t.title}{dur} · {t.priority}{tags}{Style.RESET_ALL}")


def _print_list_dropped_task(t):
    dur = f"  [{t.duration}]" if t.duration else ""
    tags = f" · #{', #'.join(t.tags)}" if t.tags else ""
    print(f"{Fore.RED + Style.DIM}x #{t.id} · {t.title}{dur} · {t.priority}{tags}{Style.RESET_ALL}")


def _print_list_offloaded_task(t):
    dur = f"  [{t.duration}]" if t.duration else ""
    tags = f" · #{', #'.join(t.tags)}" if t.tags else ""
    print(f"{Fore.WHITE + Style.DIM}→ #{t.id} · {t.title}{dur} · {t.priority}{tags}{Style.RESET_ALL}")


def _render_done_view(done, now, today_str):
    week_ago = (now - timedelta(days=7)).strftime('%Y-%m-%d')
    g_today, g_week, g_earlier = [], [], []
    for t in done:
        d = (getattr(t, 'completed_at', None) or '')[:10]
        if d == today_str:
            g_today.append(t)
        elif d >= week_ago:
            g_week.append(t)
        else:
            g_earlier.append(t)
    print()
    for title, items in (("COMPLETED TODAY", g_today),
                         ("COMPLETED THIS WEEK", g_week),
                         ("COMPLETED EARLIER", g_earlier)):
        if not items:
            continue
        _list_group_header(title, len(items), Fore.GREEN + Style.DIM)
        for t in items:
            _print_list_done_task(t)
        print()
    print(f"{Style.DIM}Total: {len(done)} completed{Style.RESET_ALL}")


def list_tasks(filter_status: Optional[str] = None,
               filter_priority: Optional[str] = None,
               filter_tag: Optional[str] = None,
               show_all: bool = False,
               sort_by: Optional[str] = None,
               show_detail: bool = False,
               show_overdue: bool = False,
               show_today: bool = False) -> None:
    """Grouped, today-first list (S13-B). Completed hidden by default; --done / --all to see them.

    Sections: TODAY / OVERDUE / UPCOMING / NO DEADLINE. Glyphs: ○ active, ✓ done (--done),
    x dropped / → offloaded (--all). OVERDUE is capped at 10 in the default view (full via
    --overdue) and shows DATES, never crushing hour counts. Filters apply within groups.
    """
    tasks = storage.load_tasks()
    print_list_missed_banner(tasks)  # PASSIVE notice only — never prompts (see: taskflow missed)
    if not tasks:
        Messenger.empty_list()
        return

    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')

    def passes(t):
        if filter_priority and (t.priority or '').lower() != filter_priority.lower():
            return False
        if filter_tag and filter_tag not in (t.tags or []):
            return False
        return True

    # --done : completed only, grouped by recency
    if filter_status == 'done':
        done = [t for t in tasks if t.completed and passes(t)]
        if not done:
            Messenger.note("You haven't completed any tasks yet.")
            return
        _render_done_view(done, now, today_str)
        return

    def is_active(t):
        return not t.completed and not getattr(t, 'dropped_at', None) and not getattr(t, 'offloaded_at', None)

    active = [t for t in tasks if is_active(t) and passes(t)]
    completed_count = sum(1 for t in tasks if t.completed and passes(t))

    # ── classify: TODAY = deadline today OR scheduled today; past → OVERDUE; future → UPCOMING ──
    today_g, overdue_g, upcoming_g, nodl_g = [], [], [], []
    for t in active:
        dt = _list_deadline_dt(t)
        scheduled_today = (getattr(t, 'scheduled_date', None) == today_str)
        if dt is not None:
            d = dt.strftime('%Y-%m-%d')
            if d == today_str or scheduled_today:
                today_g.append((t, dt))
            elif d < today_str:
                overdue_g.append((t, dt))
            else:
                upcoming_g.append((t, dt))
        else:
            if scheduled_today:
                today_g.append((t, None))
            else:
                nodl_g.append((t, None))

    prio_rank = {'critical': 0, 'high': 0, 'strategic': 1, 'medium': 1, 'noise': 2, 'low': 2, 'purge': 3}

    def sort_group(items, default):
        if sort_by == 'priority':
            items.sort(key=lambda x: (prio_rank.get((x[0].priority or '').lower(), 1), x[1] or now))
        elif sort_by == 'due':
            items.sort(key=lambda x: (x[1] is None, x[1] or now))
        elif sort_by == 'created':
            items.sort(key=lambda x: (x[0].created_at or ''), reverse=True)
        else:
            default()

    def _default_nodl():
        nodl_g.sort(key=lambda x: (x[0].created_at or ''), reverse=True)   # newest first…
        nodl_g.sort(key=lambda x: prio_rank.get((x[0].priority or '').lower(), 1))  # …then CRITICAL→NOISE (stable)

    sort_group(today_g, lambda: today_g.sort(key=lambda x: (x[1] is None, x[1] or now)))   # deadline asc
    sort_group(overdue_g, lambda: overdue_g.sort(key=lambda x: x[1], reverse=True))         # most recent missed first
    sort_group(upcoming_g, lambda: upcoming_g.sort(key=lambda x: x[1]))                     # soonest first
    sort_group(nodl_g, _default_nodl)

    # ── quick views (--today / --overdue) ──
    if show_today:
        print()
        _list_group_header("TODAY", len(today_g), Fore.CYAN + Style.BRIGHT)
        if today_g:
            for t, _dt in today_g:
                _print_list_active_task(t, now, show_detail)
        else:
            print(f"{Style.DIM}No missions scheduled for today.{Style.RESET_ALL}")
        print()
        print_list_missed_footer(tasks)
        return

    if show_overdue:
        print()
        _list_group_header("OVERDUE", len(overdue_g), Fore.RED)
        if overdue_g:
            for t, _dt in overdue_g:
                _print_list_active_task(t, now, show_detail)
        else:
            print(f"{Style.DIM}Nothing overdue. Clean slate.{Style.RESET_ALL}")
        print()
        print_list_missed_footer(tasks)
        return

    # ── default grouped view ──
    OVERDUE_CAP = 10
    print()
    printed = False
    for title, items, color in (
        ("TODAY", today_g, Fore.CYAN + Style.BRIGHT),
        ("OVERDUE", overdue_g, Fore.RED),
        ("UPCOMING", upcoming_g, Fore.CYAN + Style.DIM),
        ("NO DEADLINE", nodl_g, Fore.WHITE + Style.DIM),
    ):
        if not items:
            continue
        printed = True
        _list_group_header(title, len(items), color)
        shown, hidden_overdue = items, 0
        if title == "OVERDUE" and not show_all and len(items) > OVERDUE_CAP:
            shown = items[:OVERDUE_CAP]
            hidden_overdue = len(items) - OVERDUE_CAP
        for t, _dt in shown:
            _print_list_active_task(t, now, show_detail)
        if hidden_overdue:
            print(f"{Fore.RED + Style.DIM}   {hidden_overdue} more overdue — use --overdue to see all{Style.RESET_ALL}")
        print()

    if not printed:
        if filter_priority or filter_tag:
            Messenger.note("No tasks match your filters.")
        else:
            Messenger.no_pending_tasks()

    total_active = len(today_g) + len(overdue_g) + len(upcoming_g) + len(nodl_g)
    plural = "s" if total_active != 1 else ""

    # ── --all : completed + dropped + offloaded at the very bottom ──
    if show_all:
        done = [t for t in tasks if t.completed and passes(t)]
        done.sort(key=lambda t: (getattr(t, 'completed_at', None) or ''), reverse=True)
        if done:
            _list_group_header("COMPLETED", len(done), Fore.GREEN + Style.DIM)
            for t in done:
                _print_list_done_task(t)
            print()
        dropped = [t for t in tasks if getattr(t, 'dropped_at', None) and not t.completed and passes(t)]
        if dropped:
            _list_group_header("DROPPED", len(dropped), Fore.RED + Style.DIM)
            for t in dropped:
                _print_list_dropped_task(t)
            print()
        offloaded = [t for t in tasks if getattr(t, 'offloaded_at', None) and not t.completed and passes(t)]
        if offloaded:
            _list_group_header("OFFLOADED", len(offloaded), Fore.WHITE + Style.DIM)
            for t in offloaded:
                _print_list_offloaded_task(t)
            print()
        tail = f"Active: {total_active} task{plural}  ·  Completed: {completed_count}"
        if dropped or offloaded:
            tail += f"  ·  Dropped: {len(dropped)}  ·  Offloaded: {len(offloaded)}"
        print(f"{Style.DIM}{tail}{Style.RESET_ALL}")
    else:
        tail = f"Active: {total_active} task{plural}  ·  Completed: {completed_count}"
        if completed_count:
            tail += " (hidden)"
        print(f"{Style.DIM}{tail}{Style.RESET_ALL}")
        if completed_count:
            print(f"{Style.DIM}Use --done to see completed  ·  --all to see everything{Style.RESET_ALL}")

    print_list_missed_footer(tasks)  # PASSIVE soft-deadline notice at bottom — never prompts



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

            # Calculate pressure level BEFORE marking completed
            level = get_pressure_level(task)
            task.pressure_level_at_completion = level
            task.completed_under_pressure = (level >= 2)

            # S4-D Now Window tracking
            if getattr(task, 'deadline', None):
                try:
                    deadline_dt = datetime.fromisoformat(task.deadline)
                    if deadline_dt.tzinfo is not None:
                        deadline_dt = deadline_dt.replace(tzinfo=None)
                    
                    completion_time = datetime.now()
                    window_start = completion_time - timedelta(minutes=45)
                    window_end = completion_time + timedelta(minutes=45)
                    
                    if window_start <= deadline_dt <= window_end:
                        task.executed_in_window = True
                    else:
                        task.executed_in_window = False
                    
                    drift = (completion_time - deadline_dt).total_seconds() / 60.0
                    task.window_drift_minutes = int(drift)
                except ValueError:
                    task.executed_in_window = None
                    task.window_drift_minutes = None
            else:
                task.executed_in_window = None
                task.window_drift_minutes = None

            task.completed = True
            task.status = "completed"
            task.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            task.actual_end_time = datetime.now().isoformat()
            
            if task.actual_start_time and task.duration:
                try:
                    start_dt = datetime.fromisoformat(task.actual_start_time)
                    end_dt = datetime.fromisoformat(task.actual_end_time)
                    actual_min = (end_dt - start_dt).total_seconds() / 60.0
                    
                    # Parse duration string to minutes
                    dur_str = task.duration.lower()
                    est_min = None
                    if dur_str == "15m": est_min = 15
                    elif dur_str == "30m": est_min = 30
                    elif dur_str == "1h": est_min = 60
                    elif dur_str == "2h": est_min = 120
                    elif dur_str == "3h": est_min = 180
                    elif dur_str == "4h+": est_min = 240
                    
                    if est_min:
                        task.duration_accuracy_ratio = round(actual_min / est_min, 2)
                except Exception:
                    pass
            elif not task.actual_start_time:
                task.duration_accuracy_ratio = None

            # S8-H: behavior log on completion
            _actual_min = None
            _est_min = None
            try:
                if task.actual_start_time and task.actual_end_time:
                    _s = datetime.fromisoformat(task.actual_start_time)
                    _e = datetime.fromisoformat(task.actual_end_time)
                    _actual_min = round((_e - _s).total_seconds() / 60.0, 1)
                if task.duration:
                    _est_min = {"15m": 15, "30m": 30, "1h": 60, "2h": 120, "3h": 180, "4h+": 240}.get(task.duration.lower())
            except Exception:
                pass
            log_behavior({
                "event": "task_completed",
                "task_id": task.id,
                "pressure_level": getattr(task, 'pressure_level_at_completion', None),
                "completed_under_pressure": getattr(task, 'completed_under_pressure', None),
                "duration_actual_minutes": _actual_min,
                "duration_estimated_minutes": _est_min,
                "accuracy_ratio": getattr(task, 'duration_accuracy_ratio', None)
            })

            # S10-E: Daily Execution Path adherence — record which slot this was actually done in
            if getattr(task, 'planned_slot', None):
                _now_slot = datetime.now()
                task.actual_slot = _time_bucket(_now_slot.hour)
                task.slot_drift = _slot_drift_minutes(task.planned_slot, _now_slot)

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


def stats_tasks(today=False, week=False, export=False, compute=False, accuracy=False, tags=False) -> None:
    """S12-D: Performance Telemetry — Time Integrity Score + behavior aggregates."""
    if compute:
        ensure_daily_summaries(force=True)
        print("Daily summaries recomputed.")
        return
    ensure_daily_summaries()  # keep the derived layer fresh (once per new day)
    if accuracy:
        return render_stats_accuracy()
    if tags:
        return render_stats_tags()
    if export:
        return export_stats_csv()
    if week:
        return render_stats_week()
    if today:
        return render_stats_today()
    return render_stats_main()


def show_help() -> None:
    """Show comprehensive help with premium formatting."""
    print(f"""
  TaskFlow v8.5.0 — The Execution Engine
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
    """View detailed MISSION BRIEF for a task with enrichment (E4)."""
    tasks = storage.load_tasks()
    
    task = next((t for t in tasks if t.id == task_id), None)
    if not task:
        Messenger.task_not_found(task_id)
        return
    
    DIM_LINE = Fore.WHITE + Style.DIM
    BRIGHT = Fore.WHITE + Style.BRIGHT
    CYAN_BRIGHT = Fore.CYAN + Style.BRIGHT
    R = Style.RESET_ALL
    divider = "━" * 58
    
    print()
    print(f"{DIM_LINE}{divider}{R}")
    print(f"{CYAN_BRIGHT}MISSION BRIEF · #{task.id}{R}")
    print(f"{DIM_LINE}{divider}{R}")
    
    # Core fields
    print(f"  Title:     {BRIGHT}{task.title}{R}")
    
    status_str = f"{Fore.GREEN}[V] COMPLETED{R}" if task.completed else f"{Fore.YELLOW}[ ] TODO{R}"
    if getattr(task, 'dropped_at', None):
        status_str = f"{Fore.RED}[X] DROPPED{R}"
    elif getattr(task, 'offloaded_at', None):
        status_str = f"{Fore.CYAN}[→] OFFLOADED{R}"
    print(f"  Status:    {status_str}")
    
    p_lower = (task.priority or "").lower()
    if p_lower in ["critical", "high"]:
        p_color = Fore.RED
    elif p_lower in ["strategic", "medium"]:
        p_color = Fore.CYAN
    else:
        p_color = Fore.WHITE + Style.DIM
    print(f"  Priority:  {p_color}{task.priority}{R}")
    
    if task.duration:
        print(f"  Duration:  {task.duration} estimated")
    
    if task.deadline:
        try:
            dt = datetime.fromisoformat(task.deadline)
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            dl_display = dt.strftime('%A, %d %b %Y at %H:%M')
            dl_type = getattr(task, 'deadline_type', None) or "soft"
            type_color = Fore.RED if dl_type == "hard" else Fore.YELLOW
            type_tag = f" {type_color}[{dl_type.upper()}]{R}"
            
            td = dt - datetime.now()
            rem_str = format_time_remaining(td, dt)
            p_level = get_pressure_level(task)
            if p_level >= 3:
                rem_color = Fore.RED + Style.BRIGHT
            elif p_level >= 2:
                rem_color = Fore.YELLOW + Style.BRIGHT
            elif p_level >= 1:
                rem_color = Fore.YELLOW
            else:
                rem_color = Fore.WHITE + Style.DIM
            
            if not task.completed:
                print(f"  Deadline:  {dl_display}{type_tag} ← {rem_color}{rem_str}{R}")
            else:
                print(f"  Deadline:  {dl_display}{type_tag}")
        except ValueError:
            print(f"  Deadline:  {task.deadline}")
    
    if task.tags:
        formatted_tags = ", ".join(f"#{t}" for t in task.tags)
        print(f"  Tags:      {Fore.BLUE}{formatted_tags}{R}")
    
    if task.created_at:
        try:
            cdt = datetime.fromisoformat(task.created_at)
            print(f"  Created:   {cdt.strftime('%A, %d %b %Y at %H:%M')}")
        except ValueError:
            print(f"  Created:   {task.created_at}")
    
    if task.completed_at:
        try:
            comp_dt = datetime.fromisoformat(task.completed_at)
            print(f"  Completed: {comp_dt.strftime('%A, %d %b %Y at %H:%M')}")
        except ValueError:
            print(f"  Completed: {task.completed_at}")
    
    if task.focus_minutes_spent > 0:
        print(f"  Focus:     {task.focus_minutes_spent} minutes spent")
    
    print(f"{DIM_LINE}{divider}{R}")
    
    # NOTES section (E4)
    desc = getattr(task, 'description', None)
    if desc:
        print()
        print(f"{BRIGHT}NOTES{R}")
        for line in desc.split('\n'):
            print(f"  {line}")
    
    # LINKS & REFERENCES section (E4)
    links = getattr(task, 'links', None) or []
    if links:
        print()
        print(f"{BRIGHT}LINKS & REFERENCES ({len(links)}){R}")
        for l in links:
            lnk_id = l.get("id", "?")
            lnk_type = l.get("type", "url")
            lnk_url = l.get("url", "")
            lnk_title = l.get("title")
            
            id_str = f"{DIM_LINE}[{lnk_id}]{R}"
            type_str = f"{CYAN_BRIGHT}{lnk_type:<10}{R}"
            url_str = f"→ {lnk_url}"
            print(f"  {id_str} {type_str} {url_str}")
            if lnk_title:
                print(f"  {'':>24}\"{DIM_LINE}{lnk_title}{R}\"")
    
    # CHECKLIST section (E4)
    checklist = getattr(task, 'checklist', None) or []
    if checklist:
        done_count = sum(1 for x in checklist if x.get("done"))
        total_count = len(checklist)
        print()
        print(f"{BRIGHT}CHECKLIST ({done_count}/{total_count} done){R}")
        for item in checklist:
            is_done = item.get("done", False)
            if is_done:
                print(f"  {Fore.GREEN}✓ {item.get('text', '')}{R}")
            else:
                print(f"  {DIM_LINE}· {item.get('text', '')}{R}")
    
    # Footer
    print()
    print(f"{DIM_LINE}{divider}{R}")
    
    # Postpone count and age
    footer_parts = []
    postpone_count = getattr(task, 'postpone_count', 0)
    footer_parts.append(f"Postponed: {postpone_count}×")
    
    if task.created_at:
        try:
            created_dt = datetime.fromisoformat(task.created_at)
            if created_dt.tzinfo is not None:
                created_dt = created_dt.replace(tzinfo=None)
            age_td = datetime.now() - created_dt
            age_hours = age_td.total_seconds() / 3600
            if age_hours < 1:
                age_str = f"{int(age_td.total_seconds() / 60)} minutes ago"
            elif age_hours < 24:
                age_str = f"{int(age_hours)} hours ago"
            else:
                age_str = f"{int(age_hours / 24)} days ago"
            footer_parts.append(f"Added: {age_str}")
        except ValueError:
            pass
    
    print(f"  {DIM_LINE}{' · '.join(footer_parts)}{R}")
    print(f"{DIM_LINE}{divider}{R}")


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
                
            if not task.actual_start_time:
                task.actual_start_time = datetime.now().isoformat()
                storage.save_tasks(tasks)
                
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
                begin_focus_lock(task_id, minutes)  # S11: open the focus lock/queue window (planned len for D2-01 cap)
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

    result = focus_manager.end_focus_session()
    try:
        _flush_focus_queue()  # S11-D: process queued captures + focus stats
    except Exception:
        pass
    return result


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
    task = next((t for t in tasks if t.id == task_id), None)
    if not task:
        Messenger.task_not_found(task_id)
        return False
        
    try:
        scheduled_date = __parse_date(date_str)
        mapping = storage.load_timeline()
        mapping[str(task_id)] = scheduled_date
        storage.save_timeline(mapping)
        
        task.scheduled_date = scheduled_date
        storage.save_tasks(tasks)
        
        Messenger.success(f"Task #{task_id} logically deployed to {scheduled_date}")
        return True
    except ValueError:
        Messenger.careful("Invalid date format. Use YYYY-MM-DD, 'today', or 'tomorrow'.")
        return False

def set_prime_target(task_id: int, date_str: str = 'today') -> bool:
    """Set a task as the single [PRIME TARGET] for a given date."""
    if not date_str: date_str = 'today'
    tasks = storage.load_tasks()
    task = next((t for t in tasks if t.id == task_id), None)
    if not task:
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
        
        task.prime_target_date = scheduled_date
        storage.save_tasks(tasks)
        
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
    """Normalize any priority input to the behavioral taxonomy: Critical / Strategic / Noise / Purge."""
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

# =========================================================
# S10: DAILY EXECUTION PATH
# =========================================================

DURATION_MINUTES = {"15m": 15, "30m": 30, "1h": 60, "2h": 120, "3h": 180, "4h+": 240}
VALID_DURATIONS = ("15m", "30m", "1h", "2h", "3h", "4h+")


def normalize_duration(value):
    """Map any duration input to the canonical enum (15m/30m/1h/2h/3h/4h+), or None (D1-01).

    Accepts canonical values, loose forms ("2 h", "45", "45m", "1h30", "5h 25m"), and buckets
    by total minutes so DURATION_MINUTES / path estimates stay correct. Unparseable → None.
    This is the SINGLE place free-text durations are sanitised; every writer must route here.
    """
    if value is None:
        return None
    s = str(value).strip().lower()
    if not s:
        return None
    if s in DURATION_MINUTES:
        return s
    if s in ("4h+", "4hr+", "4 h+", "4h +"):
        return "4h+"
    import re as _re
    total = 0
    matched = False
    for num, unit in _re.findall(r'(\d+)\s*(hours?|hrs?|h|minutes?|mins?|min|m)?', s):
        if not num:
            continue
        n = int(num)
        if unit and unit.startswith('h'):
            total += n * 60
        else:  # explicit minutes, or a bare number → minutes
            total += n
        matched = True
    if not matched or total <= 0:
        return None
    if total <= 22:
        return "15m"
    if total <= 45:
        return "30m"
    if total <= 90:
        return "1h"
    if total <= 150:
        return "2h"
    if total <= 210:
        return "3h"
    return "4h+"
PATH_DEEP_WORK_TAGS = {"deep-work", "deep_work", "deepwork", "code", "coding", "write",
                       "writing", "design", "build", "architect", "research"}
PATH_COMM_TAGS = {"meeting", "call", "standup", "email", "reply", "review", "sync"}
PATH_ADMIN_TAGS = {"admin", "housekeeping", "chore", "chores", "logs", "ops",
                   "cleanup", "misc", "inbox", "errand"}

# Planned-slot → expected time-of-day bucket (energy curve: hard first, light last)
_SLOT_EXPECTED_BUCKET = {"prime": "morning", "secondary": "midday", "low_effort": "evening"}
# Canonical target hour for each planned slot (used for slot_drift)
_SLOT_TARGET_HOUR = {"prime": 9, "secondary": 13, "low_effort": 17}


def _duration_minutes(task, default=30) -> int:
    """Minutes for a task's duration. No duration → `default` (S10-B step 4)."""
    d = (getattr(task, 'duration', None) or "").lower()
    return DURATION_MINUTES.get(d, default)


def _priority_tier(task) -> str:
    """Map TaskFlow's internal priorities to high/medium/low tiers."""
    p = (getattr(task, 'priority', None) or "").lower()
    if p in ("critical", "high"):
        return "high"
    if p in ("strategic", "medium"):
        return "medium"
    return "low"  # noise, low, purge, unknown


def _task_tags_lower(task) -> set:
    return {str(t).lower() for t in (getattr(task, 'tags', None) or [])}


def _is_comm(task) -> bool:
    return bool(_task_tags_lower(task) & PATH_COMM_TAGS)


def _is_short(task) -> bool:
    return (getattr(task, 'duration', None) or "").lower() in ("15m", "30m")


def score_for_path(task) -> int:
    """Cognitive-load score that determines PRIME eligibility (S10-B step 2)."""
    score = 0
    dur = (getattr(task, 'duration', None) or "").lower()
    if dur in ("2h", "3h", "4h+"):
        score += 40
    elif dur == "1h":
        score += 20
    if _priority_tier(task) == "high":
        score += 30
    if getattr(task, 'deadline_type', None) == "hard":
        score += 20
    if _task_tags_lower(task) & PATH_DEEP_WORK_TAGS:
        score += 15
    return score


def _path_deadline_key(task):
    """Sort key: tasks with a deadline first (soonest first), undated last."""
    if getattr(task, 'deadline', None):
        try:
            dt = datetime.fromisoformat(task.deadline)
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            return (0, dt)
        except Exception:
            return (1, datetime.max)
    return (1, datetime.max)


def _qualifies_secondary(task) -> bool:
    if _priority_tier(task) in ("high", "medium"):
        return True
    if _is_comm(task):
        return True
    if (getattr(task, 'duration', None) or "").lower() == "1h":
        return True
    if getattr(task, 'deadline_type', None) == "hard":
        return True
    return False


def _qualifies_low(task) -> bool:
    if _is_short(task):
        return True
    if _priority_tier(task) == "low":
        return True
    if _task_tags_lower(task) & PATH_ADMIN_TAGS:
        return True
    return False


def _path_eligible(tasks, timeline, today_str):
    """Tasks eligible for today's path — mirrors run_today_view inclusion (S10-B step 1)."""
    elig = []
    for task in tasks:
        if task.completed:
            continue
        if getattr(task, 'dropped_at', None) or getattr(task, 'offloaded_at', None):
            continue
        if getattr(task, 'status', None) in ('completed', 'done', 'dropped', 'offloaded'):
            continue

        included = False
        # (a) deadline date is today (future-beyond-today excluded here)
        if task.deadline:
            try:
                dt = datetime.fromisoformat(task.deadline)
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                if dt.strftime('%Y-%m-%d') == today_str:
                    included = True
            except Exception:
                pass
        # (b) scheduled today
        if not included:
            tslot = timeline.get(str(task.id))
            if tslot and tslot.startswith(today_str):
                included = True
            elif getattr(task, 'scheduled_date', None) == today_str:
                included = True
        # (c) prime today
        if not included:
            tslot = timeline.get(str(task.id))
            if tslot == f"{today_str}_prime" or getattr(task, 'prime_target_date', None) == today_str:
                included = True
        # (d) untimed, created today (float task)
        if not included and not task.deadline:
            if task.created_at and task.created_at.startswith(today_str):
                included = True

        if included:
            elig.append(task)
    return elig


def _today_prime_task(elig, timeline, today_str):
    """The task explicitly set as PRIME for today, if it's eligible."""
    for t in elig:
        tslot = timeline.get(str(t.id))
        if tslot == f"{today_str}_prime" or getattr(t, 'prime_target_date', None) == today_str:
            return t
    return None


def generate_execution_path(tasks, config, day_multiplier=1.0, day_mode=None) -> dict:
    """Build today's execution path (S10-B). Pure: returns id-lists, no persistence.

    S14-C: an optional day-of-week modifier nudges PRIME selection (a longer task is allowed
    on a high-performance day, a shorter one preferred on a light day) and caps SECONDARY at 3
    on a light day. The multiplier adjusts scores — it never hard-overrides slot membership.
    """
    timeline = storage.load_timeline()
    today_str = datetime.now().strftime('%Y-%m-%d')
    sections = {"prime": [], "secondary": [], "low_effort": [], "unscheduled": []}

    elig = _path_eligible(tasks, timeline, today_str)
    if not elig:
        return sections

    def _eff_score(t):
        s = score_for_path(t) * day_multiplier
        if day_mode == 'best':
            s += _duration_minutes(t) * 0.10   # high-performance day → allow a longer PRIME
        elif day_mode == 'worst':
            s -= _duration_minutes(t) * 0.10   # light day → prefer a shorter PRIME
        return s

    # PRIME — honor explicit prime, else best day-adjusted cognitive-load score
    prime_task = _today_prime_task(elig, timeline, today_str)
    if prime_task is None:
        prime_task = max(elig, key=_eff_score)
    sections["prime"] = [prime_task.id]
    remaining = [t for t in elig if t.id != prime_task.id]

    # SECONDARY — deadline asc, then heavier load first; capped (3 on a light day, else 4)
    sec_cap = 3 if day_mode == 'worst' else 4
    secondary = []
    for t in sorted(remaining, key=lambda x: (_path_deadline_key(x), -score_for_path(x))):
        if len(secondary) >= sec_cap:
            break
        if _qualifies_secondary(t):
            secondary.append(t)
    sec_ids = {t.id for t in secondary}
    sections["secondary"] = [t.id for t in secondary]

    # LOW EFFORT (max 6) — wind-down work
    rem2 = [t for t in remaining if t.id not in sec_ids]
    low = []
    for t in rem2:
        if len(low) >= 6:
            break
        if _qualifies_low(t):
            low.append(t)
    low_ids = {t.id for t in low}
    sections["low_effort"] = [t.id for t in low]

    # UNSCHEDULED — eligible but unplaced
    sections["unscheduled"] = [t.id for t in rem2 if t.id not in low_ids]
    return sections


def _section_minutes(by_id, id_list) -> int:
    return sum(_duration_minutes(by_id[i]) for i in id_list if i in by_id)


def _time_bucket(hour: int) -> str:
    """Map an hour-of-day to a slot bucket (S10-A actual_slot)."""
    if 6 <= hour < 12:
        return "morning"
    if 12 <= hour < 16:
        return "midday"
    return "evening"  # 16:00–05:59 (late work folds into evening)


def _slot_drift_minutes(planned_slot, dt) -> Optional[int]:
    """Minutes between the planned slot's canonical target time and `dt`."""
    h = _SLOT_TARGET_HOUR.get(planned_slot)
    if h is None:
        return None
    target = dt.replace(hour=h, minute=0, second=0, microsecond=0)
    return int((dt - target).total_seconds() // 60)


def _compute_path_adherence(tasks, config) -> Optional[float]:
    """Fraction of completed path tasks done in their planned time-of-day bucket."""
    path_ids = config.get('path_tasks') or []
    if not path_ids:
        return None
    by_id = {t.id: t for t in tasks}
    completed = [by_id[i] for i in path_ids if i in by_id and by_id[i].completed]
    if not completed:
        return None
    hits = 0
    for t in completed:
        expected = _SLOT_EXPECTED_BUCKET.get(getattr(t, 'planned_slot', None))
        if expected and getattr(t, 'actual_slot', None) == expected:
            hits += 1
    return round(hits / len(completed), 2)


def generate_and_persist_path(compute_prev_adherence: bool = True):
    """Generate today's path, stamp planned_slot on tasks, persist to config.

    Returns (sections, total_minutes). Used by `taskflow path` and POST /api/path/generate.
    """
    tasks = storage.load_tasks()
    config = storage.load_config()
    today_str = datetime.now().strftime('%Y-%m-%d')

    # S10-E: settle adherence for the previous day's path before regenerating
    if compute_prev_adherence:
        prev_date = config.get('path_generated_date')
        if prev_date and prev_date != today_str:
            adh = _compute_path_adherence(tasks, config)
            if adh is not None:
                config['path_adherence_today'] = adh

    # S14-C: day-of-week modifier (subtle; only applies when that weekday has >=2 samples)
    day_multiplier, day_mode, day_note = 1.0, None, None
    try:
        dow_stats = compute_day_of_week_stats(storage.load_daily_summaries())
        today_wd = datetime.now().weekday()
        bd, wd_ = dow_stats.get('best_day'), dow_stats.get('worst_day')
        worst_avg = dow_stats.get('worst_day_avg_tis')
        if bd is not None and today_wd == bd:
            day_multiplier, day_mode = 1.2, 'best'
            day_note = "High-performance day based on your patterns."
        elif wd_ is not None and today_wd == wd_ and worst_avg is not None and worst_avg < 65:
            day_multiplier, day_mode = 0.8, 'worst'
            day_note = "Light day — protect energy."
    except Exception:
        pass

    sections = generate_execution_path(tasks, config, day_multiplier, day_mode)

    # Stamp planned_slot (None clears stale slots from previous days)
    slot_of = {}
    for s in ("prime", "secondary", "low_effort"):
        for i in sections[s]:
            slot_of[i] = s
    for t in tasks:
        t.planned_slot = slot_of.get(t.id)
    storage.save_tasks(tasks)

    config['path_generated_date'] = today_str
    config['path_tasks'] = (sections['prime'] + sections['secondary']
                            + sections['low_effort'] + sections['unscheduled'])
    config['path_sections'] = sections
    config['path_day_mode'] = day_mode
    config['path_day_note'] = day_note
    storage.save_config(config)

    by_id = {t.id: t for t in tasks}
    total = (_section_minutes(by_id, sections['prime'])
             + _section_minutes(by_id, sections['secondary'])
             + _section_minutes(by_id, sections['low_effort']))
    return sections, total


# ---- S10-C rendering helpers ----

def _fmt_minutes(m: int) -> str:
    if m <= 0:
        return "0m"
    h, mm = divmod(m, 60)
    if h and mm:
        return f"{h}h {mm}m"
    if h:
        return f"{h}h"
    return f"{mm}m"


def _path_prio_color(task):
    tier = _priority_tier(task)
    if tier == "high":
        return Fore.RED
    if tier == "medium":
        return Fore.YELLOW
    return Fore.WHITE + Style.DIM


def _path_task_line(task) -> str:
    """`  → Title              [dur · PRIO · HARD]` with spec colors."""
    dur = task.duration if getattr(task, 'duration', None) else "—"
    prio = (task.priority or "").upper()
    arrow = f"{_path_prio_color(task)}→{Style.RESET_ALL}"
    title = (task.title or "")[:34]
    dur_c = f"{Fore.CYAN}{dur}{Style.RESET_ALL}"
    prio_c = f"{_path_prio_color(task)}{prio}{Style.RESET_ALL}"
    hard_c = f" · {Fore.RED}HARD{Style.RESET_ALL}" if getattr(task, 'deadline_type', None) == "hard" else ""
    return f"  {arrow} {title:<34}  [{dur_c} · {prio_c}{hard_c}]"


def _path_unscheduled_line(task) -> str:
    prio = (task.priority or "").capitalize()
    tagp = f" · #{task.tags[0]}" if getattr(task, 'tags', None) else ""
    arrow = f"{_path_prio_color(task)}→{Style.RESET_ALL}"
    title = (task.title or "")[:34]
    return f"  {arrow} {title:<34}  {Fore.WHITE + Style.DIM}[{prio}{tagp}]{Style.RESET_ALL}"


def _due_phrase(task) -> Optional[str]:
    if not getattr(task, 'deadline', None):
        return None
    try:
        dt = datetime.fromisoformat(task.deadline)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
    except Exception:
        return None
    now = datetime.now()
    today0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    d0 = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    tstr = dt.strftime('%H:%M')
    if d0 == today0:
        human = f"Today at {tstr}"
    elif d0 == today0 + timedelta(days=1):
        human = f"Tomorrow at {tstr}"
    else:
        human = dt.strftime('%a %d %b').replace(' 0', ' ') + f" at {tstr}"
    return f"{human} · {format_time_remaining(dt - now, dt)}"


def _path_bar():
    return Fore.CYAN + ("━" * 44) + Style.RESET_ALL


def _path_daystr():
    now = datetime.now()
    return now.strftime('%A, ') + str(now.day) + now.strftime(' %b')


def _render_path_full(by_id, sections):
    bar = _path_bar()
    print()
    print(bar)
    print(f"{Fore.CYAN + Style.BRIGHT}⚡  EXECUTION PATH · {_path_daystr()}{Style.RESET_ALL}")
    _cfg = storage.load_config()
    _note, _mode = _cfg.get('path_day_note'), _cfg.get('path_day_mode')
    if _note:
        _ncol = Fore.GREEN if _mode == 'best' else (Fore.YELLOW if _mode == 'worst' else Fore.CYAN)
        print(f"{_ncol}⚡  {_note}{Style.RESET_ALL}")
    print(bar)
    print("Generated for today. Run --refresh to regenerate.")
    print(bar)
    print()

    prime_tasks = [by_id[i] for i in sections.get('prime', []) if i in by_id]
    if prime_tasks:
        pt = prime_tasks[0]
        est = _fmt_minutes(_duration_minutes(pt))
        print(f"{Fore.YELLOW + Style.BRIGHT}[★ PRIME TARGET]{Style.RESET_ALL}  — deep work · est. {est}")
        print(_path_task_line(pt))
        due = _due_phrase(pt)
        if due:
            print(f"    {Fore.WHITE + Style.DIM}Due: {due}{Style.RESET_ALL}")
        print()

    sec = [by_id[i] for i in sections.get('secondary', []) if i in by_id]
    if sec:
        est = _fmt_minutes(sum(_duration_minutes(t) for t in sec))
        print(f"{Fore.WHITE + Style.BRIGHT}[SECONDARY]{Style.RESET_ALL}  — est. {est}")
        for t in sec:
            print(_path_task_line(t))
        print()

    low = [by_id[i] for i in sections.get('low_effort', []) if i in by_id]
    if low:
        est = _fmt_minutes(sum(_duration_minutes(t) for t in low))
        print(f"{Fore.WHITE + Style.DIM}[LOW EFFORT]{Style.RESET_ALL}  — est. {est}")
        for t in low:
            print(_path_task_line(t))
        print()

    uns = [by_id[i] for i in sections.get('unscheduled', []) if i in by_id]
    if uns:
        print(f"{Fore.WHITE + Style.DIM}[UNSCHEDULED]{Style.RESET_ALL}")
        for t in uns:
            print(_path_unscheduled_line(t))
        print()

    total = (sum(_duration_minutes(t) for t in prime_tasks)
             + sum(_duration_minutes(t) for t in sec)
             + sum(_duration_minutes(t) for t in low))
    print(bar)
    print(f"{Fore.CYAN}Total estimated: {_fmt_minutes(total)}{Style.RESET_ALL}")
    if total < 360:
        print(f"{Fore.GREEN}Your day has capacity. Execute in this order.{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}Heavy day. Consider moving LOW EFFORT tasks.{Style.RESET_ALL}")
    print(bar)
    print()


def _render_path_focus(by_id, sections):
    bar = _path_bar()
    prime_tasks = [by_id[i] for i in sections.get('prime', []) if i in by_id]
    print()
    print(bar)
    print(f"{Fore.YELLOW + Style.BRIGHT}⚡  PRIME TARGET · {_path_daystr()}{Style.RESET_ALL}")
    print(bar)
    if prime_tasks:
        pt = prime_tasks[0]
        print(_path_task_line(pt))
        due = _due_phrase(pt)
        if due:
            print(f"    {Fore.WHITE + Style.DIM}Due: {due}{Style.RESET_ALL}")
    print(bar)
    print()


def command_path(refresh: bool = False, focus: bool = False):
    """`taskflow path` — show/generate the Daily Execution Path (S10-C)."""
    config = storage.load_config()
    today_str = datetime.now().strftime('%Y-%m-%d')
    already = (config.get('path_generated_date') == today_str and config.get('path_sections'))

    if already and not refresh:
        sections = config.get('path_sections') or {}
    else:
        sections, _total = generate_and_persist_path()

    tasks = storage.load_tasks()
    by_id = {t.id: t for t in tasks}

    if not sections.get('prime'):
        print(f"\n{Fore.WHITE}No missions for today. Add one: {Fore.CYAN}taskflow add{Style.RESET_ALL}\n")
        return

    if focus:
        _render_path_focus(by_id, sections)
    else:
        _render_path_full(by_id, sections)


# =========================================================
# S11: FOCUS WINDOW LOCK
# =========================================================
# NOTE: TimeTracker already owns ~/.taskflow/focus_state.json (active_session/start_time),
# so the S11 lock+queue layer lives in a separate ~/.taskflow/focus_lock.json. Active state,
# task_id and ends_at are DERIVED from the live TimeTracker session — single source of truth.

def _default_focus_lock():
    return {"task_id": None, "started_at": None, "queued_tasks": [], "queued_actions": []}


def _focus_session_info():
    """Active focus info derived from TimeTracker, or None. No queue side effects."""
    try:
        st = time_tracker.check_focus()
    except Exception:
        st = None
    if st and st.get('status') == 'active':
        return {
            "active": True,
            "task_id": st.get('task_id'),
            "task_title": st.get('task_title'),
            "minutes_left": st.get('remaining_minutes'),
            "seconds_left": st.get('remaining_seconds'),
            "mode": st.get('mode', 'gentle'),
        }
    return None


def _focus_remaining_str(info):
    if not info:
        return "--:--"
    m = info.get('minutes_left') or 0
    s = info.get('seconds_left') or 0
    return f"{int(m):02d}:{int(s):02d}"


def _flush_focus_queue(lock=None):
    """Process queued captures + update the focused task's focus stats, then reset the lock.

    Runs when a session ends (timer expiry detected lazily, or explicit `focus --end`).
    """
    if lock is None:
        lock = storage.load_focus_lock()
    queued = lock.get('queued_tasks') or []
    task_id = lock.get('task_id')
    started = lock.get('started_at')

    added = []
    if queued:
        tasks = storage.load_tasks()
        manager = TaskManager(tasks)
        for q in queued:
            try:
                t = Task(id=0,
                         title=q.get('title') or 'Captured thought',
                         priority=normalize_priority(q.get('priority') or 'Medium'),
                         tags=q.get('tags') or [])
                t.duration = normalize_duration(q.get('duration'))
                if q.get('deadline'):
                    t.deadline = q['deadline']
                    t.deadline_type = q.get('deadline_type', 'soft')
                tid = manager.add_task(t)
                added.append((t.title, tid))
            except Exception:
                continue
        storage.save_tasks(manager.tasks)

    # S11-D step 4: update the focused task's focus stats
    if task_id is not None and started:
        try:
            tasks = storage.load_tasks()
            for t in tasks:
                if t.id == task_id:
                    t.focus_session_count = (getattr(t, 'focus_session_count', 0) or 0) + 1
                    try:
                        elapsed = (datetime.now() - datetime.fromisoformat(started)).total_seconds() / 60.0
                        planned = lock.get('planned_minutes')
                        # D2-01: a lazy flush can fire long after the timer expired — never credit
                        # more than the planned session (+2 min grace) so the stat stays honest.
                        capped = elapsed if not planned else min(elapsed, planned + 2)
                        t.focus_total_minutes = (getattr(t, 'focus_total_minutes', 0) or 0) + max(0, int(capped))
                    except Exception:
                        pass
                    t.last_focus_at = datetime.now().isoformat()
                    break
            storage.save_tasks(tasks)
        except Exception:
            pass

    # S11-D step 2: report queued missions that were added
    if added:
        bar = Fore.CYAN + ("─" * 44) + Style.RESET_ALL
        print("\n" + bar)
        print(f"{Fore.GREEN}✓ Focus session ended.{Style.RESET_ALL}")
        print(f"{len(added)} queued mission(s) added to your board:\n")
        for title, tid in added:
            label = (title or "")[:34]
            print(f"{Fore.GREEN}  · {label:<34} (#{tid}){Style.RESET_ALL}")
        print(bar + "\n")

    storage.save_focus_lock(_default_focus_lock())
    return added


def focus_lock_active():
    """Return active focus info, or None. Flushes an orphaned queue once a session is over.

    Called at CLI startup on every command (lazy expiry handling — there is no daemon).
    """
    info = _focus_session_info()
    if info:
        return info
    lock = storage.load_focus_lock()
    if (lock.get('queued_tasks') or lock.get('task_id') is not None):
        _flush_focus_queue(lock)
    return None


def begin_focus_lock(task_id, minutes=None):
    """Record the start of a focus session for the lock/queue layer (called from focus_task).

    `minutes` = the planned session length, stored so _flush_focus_queue can cap
    focus_total_minutes when a timer is flushed lazily, long after it expired (D2-01).
    """
    storage.save_focus_lock({
        "task_id": task_id,
        "started_at": datetime.now().isoformat(),
        "planned_minutes": minutes,
        "queued_tasks": [],
        "queued_actions": []
    })


def print_focus_header(info):
    """`── Focus session active (MM:SS remaining) ──` prepended to list/today during focus."""
    mmss = _focus_remaining_str(info)
    print(f"{Fore.CYAN}── Focus session active ({mmss} remaining) ──{Style.RESET_ALL}")


def focus_complete_nudge():
    print(f"{Fore.GREEN}✓ Mission complete during focus. Stay locked in.{Style.RESET_ALL}")


def focus_capture_add(info=None):
    """`taskflow add` during focus → capture a single title into the queue (no full flow)."""
    mmss = _focus_remaining_str(info)
    print(f"{Fore.CYAN}── Focus session active ({mmss} remaining) ──{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Adding tasks is locked during focus.{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Your thought has been queued.{Style.RESET_ALL}\n")
    title = get_valid_input("Capture (title): ").strip()
    title = validate_title(title)
    if not title:
        print("Nothing captured.")
        return
    lock = storage.load_focus_lock()
    lock.setdefault('queued_tasks', []).append({"title": title, "priority": "Medium", "source": "add"})
    storage.save_focus_lock(lock)
    print(f"\n{Fore.GREEN}Task queued: {title}{Style.RESET_ALL}\n")
    print("It will be added automatically when focus ends.")
    print(f"Run: {Fore.CYAN}taskflow queue{Style.RESET_ALL}  to see all queued items.")


def focus_capture_dump(info, text, duration=None, deadline=None, is_hard=False):
    """`taskflow dump` during focus → queue the parsed thought (fast path stays fast)."""
    import re
    text = text or ""
    tags = ["inbox"]
    for t in re.findall(r'#(\w+)', text):
        if t.lower() not in [x.lower() for x in tags]:
            tags.append(t)
    priority = "Medium"
    pr = re.findall(r'!(low|medium|high|noise|strategic|critical|l|m|h|p|purge)(?!\w)', text, re.IGNORECASE)
    if pr:
        priority = pr[-1]
    clean = re.sub(r'#\w+', '', text)
    clean = re.sub(r'!(low|medium|high|noise|strategic|critical|l|m|h|p|purge)(?!\w)', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\s+', ' ', clean).strip()
    clean = validate_title(clean)
    if not clean:
        print("Nothing captured.")
        return
    entry = {"title": clean, "priority": normalize_priority(priority.capitalize()), "tags": tags, "source": "dump"}
    if duration:
        entry["duration"] = duration.lower()
    if deadline:
        pd = parse_deadline(deadline)
        if pd:
            entry["deadline"] = pd.isoformat()
            entry["deadline_type"] = "hard" if is_hard else "soft"
    lock = storage.load_focus_lock()
    lock.setdefault('queued_tasks', []).append(entry)
    storage.save_focus_lock(lock)
    print(f'{Fore.CYAN}── Focus active ──{Style.RESET_ALL} "{clean}" queued.')


def command_queue(clear=False):
    """`taskflow queue` — view (or --clear) items captured during focus (S11-C)."""
    info = _focus_session_info()
    lock = storage.load_focus_lock()
    queued = lock.get('queued_tasks') or []

    if clear:
        if not queued:
            print("No queued items to clear.")
            return
        n = len(queued)
        confirm = get_valid_input(f"Clear {n} queued items? [Y/n]: ", "y").strip().lower()
        if confirm in ("y", "yes", ""):
            lock['queued_tasks'] = []
            storage.save_focus_lock(lock)
            print(f"{n} queued items cleared.")
        else:
            print("Cancelled.")
        return

    if not info:
        print("No active focus session. Queue is empty.")
        return

    mmss = _focus_remaining_str(info)
    head = f"── Focus active · {mmss} remaining "
    head += "─" * max(0, 46 - len(head))
    print(f"{Fore.CYAN}{head}{Style.RESET_ALL}")
    print(f"Queued for after focus ({len(queued)} items):\n")
    if queued:
        for i, q in enumerate(queued, 1):
            print(f"  [{i}]  {q.get('title')}")
    else:
        print("  (nothing queued yet)")
    print("\nThese will be added automatically when focus ends.")
    print(f"{Fore.CYAN}{'─' * 46}{Style.RESET_ALL}")


# ---- S11-F API helpers (used by server.py) ----

def focus_status_payload():
    """GET /api/focus-status → {active, task_id, ends_at, queued_count}."""
    info = _focus_session_info()
    lock = storage.load_focus_lock()
    qcount = len(lock.get('queued_tasks') or [])
    if not info:
        return {"active": False, "task_id": None, "ends_at": None, "queued_count": qcount}
    ml = info.get('minutes_left') or 0
    sl = info.get('seconds_left') or 0
    ends = (datetime.now() + timedelta(minutes=ml, seconds=sl)).isoformat()
    return {"active": True, "task_id": info.get('task_id'), "ends_at": ends, "queued_count": qcount}


def enqueue_focus_task(data):
    """POST /api/focus/queue → append a task to the focus queue. Returns new queue length."""
    data = data or {}
    lock = storage.load_focus_lock()
    entry = {
        "title": (str(data.get('title') or '').strip() or 'Captured thought'),
        "priority": normalize_priority(data.get('priority') or 'Medium'),
        "tags": data.get('tags') or [],
        "source": "ui"
    }
    if data.get('duration'):
        entry["duration"] = str(data['duration']).lower()
    if data.get('deadline'):
        entry["deadline"] = data['deadline']
        entry["deadline_type"] = data.get('deadline_type', 'soft')
    lock.setdefault('queued_tasks', []).append(entry)
    storage.save_focus_lock(lock)
    return len(lock['queued_tasks'])


# =========================================================
# S12: TIME INTEGRITY SCORE + BEHAVIOR DATA STORE
# =========================================================

def _behavior_log_path():
    return storage.data_dir / "behavior_log.jsonl"


def _all_behavior_entries():
    """Read every behavior_log.jsonl entry (read-only — Rule #3)."""
    out = []
    f = _behavior_log_path()
    if not f.exists():
        return out
    try:
        with open(f, 'r', encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        pass
    return out


def get_behavior_log_entries(date):
    """All behavior_log entries whose timestamp falls on `date` (YYYY-MM-DD)."""
    return [e for e in _all_behavior_entries()
            if isinstance(e.get('ts'), str) and e.get('ts', '')[:10] == date]


def _parse_dt_any(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        try:
            return datetime.strptime(s, '%Y-%m-%d %H:%M')
        except Exception:
            return None


def calculate_time_integrity_score(s) -> int:
    """Weighted 0–100 score (S12-B). Division-safe."""
    dm = s.get('deadlines_met', 0) or 0
    dmiss = s.get('deadlines_missed', 0) or 0
    deadline_pts = (dm / max(1, dm + dmiss)) * 40
    deadline_pts -= min(20, (s.get('hard_deadlines_missed', 0) or 0) * 5)

    tc = s.get('tasks_completed', 0) or 0
    tmiss = s.get('tasks_missed', 0) or 0
    exec_pts = (tc / max(1, tc + tmiss)) * 30

    postpone_pts = 20 - min(20, (s.get('tasks_postponed', 0) or 0) * 3)

    rec_pts = 0
    if s.get('recovery_activated'):
        rec_pts = 10 if s.get('recovery_successful') else -5

    return max(0, min(100, round(deadline_pts + exec_pts + postpone_pts + rec_pts)))


def compute_daily_summary(date, tasks, behavior_log_entries) -> dict:
    """Aggregate one day's behavior into the S12-A schema."""
    def d10(v):
        return (v or "")[:10]

    completed = [t for t in tasks if t.completed and d10(getattr(t, 'completed_at', None)) == date]
    dropped = [t for t in tasks if d10(getattr(t, 'dropped_at', None)) == date]
    offloaded = [t for t in tasks if d10(getattr(t, 'offloaded_at', None)) == date]

    deadlines_met = deadlines_missed = hard_missed = 0
    for t in tasks:
        dl = _parse_dt_any(getattr(t, 'deadline', None))
        if not dl:
            continue
        if dl.tzinfo is not None:
            dl = dl.replace(tzinfo=None)
        if dl.strftime('%Y-%m-%d') != date:
            continue
        met = False
        if t.completed and getattr(t, 'completed_at', None):
            cdt = _parse_dt_any(t.completed_at)
            met = (cdt is not None and cdt <= dl) or cdt is None
        if met:
            deadlines_met += 1
        else:
            deadlines_missed += 1
            if getattr(t, 'deadline_type', None) == 'hard':
                hard_missed += 1

    tasks_postponed = sum(1 for e in behavior_log_entries if 'postpone' in str(e.get('event', '')).lower())

    focus_entries = [e for e in behavior_log_entries if str(e.get('event', '')) in ('focus_session', 'focus_complete')]
    focus_sessions = len(focus_entries)
    focus_minutes_total = int(sum(float(e.get('minutes', 0) or 0) for e in focus_entries))

    drifts = [t.slot_drift for t in completed if getattr(t, 'slot_drift', None) is not None]
    avg_drift = round(sum(drifts) / len(drifts), 1) if drifts else None

    hours = []
    for e in behavior_log_entries:
        if e.get('event') == 'task_completed':
            dt = _parse_dt_any(e.get('ts'))
            if dt:
                hours.append(dt.hour)
    if not hours:
        for t in completed:
            cdt = _parse_dt_any(t.completed_at)
            if cdt:
                hours.append(cdt.hour)
    best_hour = None
    if hours:
        from collections import Counter
        best_hour = Counter(hours).most_common(1)[0][0]

    rec_activated = rec_success = False
    try:
        if storage.recovery_log_file.exists():
            with open(storage.recovery_log_file, 'r') as rf:
                for s in json.load(rf):
                    if isinstance(s, dict) and s.get('date') == date:
                        rec_activated = True
                        if s.get('was_successful'):
                            rec_success = True
    except Exception:
        pass

    summary = {
        "date": date,
        "tasks_completed": len(completed),
        "tasks_missed": deadlines_missed,
        "tasks_postponed": tasks_postponed,
        "tasks_dropped": len(dropped),
        "tasks_offloaded": len(offloaded),
        "focus_sessions": focus_sessions,
        "focus_minutes_total": focus_minutes_total,
        "deadlines_met": deadlines_met,
        "deadlines_missed": deadlines_missed,
        "hard_deadlines_missed": hard_missed,
        "avg_start_drift_minutes": avg_drift,
        "recovery_activated": rec_activated,
        "recovery_successful": rec_success,
        "path_adherence": None,
        "time_integrity_score": None,
        "best_hour": best_hour,
        "worst_hour": None,
    }
    summary["time_integrity_score"] = calculate_time_integrity_score(summary)
    return summary


def _most_productive_hour(n_days=7):
    cutoff = (datetime.now() - timedelta(days=n_days)).date()
    from collections import Counter
    c = Counter()
    for e in _all_behavior_entries():
        if e.get('event') == 'task_completed':
            dt = _parse_dt_any(e.get('ts'))
            if dt and dt.date() >= cutoff:
                c[dt.hour] += 1
    return c.most_common(1)[0][0] if c else None


def _most_avoided_tag(n_days=7):
    cutoff = (datetime.now() - timedelta(days=n_days)).strftime('%Y-%m-%d')
    from collections import Counter
    c = Counter()
    for t in storage.load_tasks():
        avoided = False
        if getattr(t, 'dropped_at', None) and t.dropped_at[:10] >= cutoff:
            avoided = True
        if (getattr(t, 'postpone_count', 0) or 0) >= 1:
            avoided = True
        if avoided:
            for tag in (t.tags or []):
                if tag.lower() != 'inbox':
                    c[tag] += 1
    return c.most_common(1)[0][0] if c else None


def compute_weekly_stats(daily_summaries) -> dict:
    """Aggregate the last 7 daily summaries (S12-C)."""
    days = sorted([d for d in daily_summaries if isinstance(d, dict)], key=lambda s: s.get('date', ''))[-7:]
    if not days:
        return None
    scores = [(d.get('time_integrity_score') or 0) for d in days]
    avg = round(sum(scores) / len(scores), 1)
    best = max(days, key=lambda d: d.get('time_integrity_score') or 0)
    worst = min(days, key=lambda d: d.get('time_integrity_score') or 0)

    last3, prev = scores[-3:], scores[:-3]
    trend = 'stable'
    if last3 and prev:
        a, b = sum(last3) / len(last3), sum(prev) / len(prev)
        if a > b + 5:
            trend = 'improving'
        elif a < b - 5:
            trend = 'declining'

    drifts = [d.get('avg_start_drift_minutes') for d in days if d.get('avg_start_drift_minutes') is not None]
    return {
        "avg_score": avg,
        "best_day": {"date": best.get('date'), "score": best.get('time_integrity_score') or 0},
        "worst_day": {"date": worst.get('date'), "score": worst.get('time_integrity_score') or 0},
        "trend": trend,
        "total_completed": sum(d.get('tasks_completed', 0) or 0 for d in days),
        "total_focus_minutes": sum(d.get('focus_minutes_total', 0) or 0 for d in days),
        "avg_start_drift": (round(sum(drifts) / len(drifts), 1) if drifts else None),
        "most_productive_hour": _most_productive_hour(7),
        "most_avoided_tag": _most_avoided_tag(7),
        "recovery_sessions": sum(1 for d in days if d.get('recovery_activated')),
        "hard_deadlines_missed_week": sum(d.get('hard_deadlines_missed', 0) or 0 for d in days),
        "days": days,
    }


_DOW_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def compute_day_of_week_stats(daily_summaries) -> dict:
    """S14-B — aggregate execution performance by day of week (0=Mon … 6=Sun).

    Only days with sample_size >= 2 are 'meaningful' for best/worst and recommendations
    (Rule #5). Sparser days are still returned (sample_size < 2, None metrics) so the UI can
    show "Building pattern…" rather than a misleading number.
    """
    from collections import defaultdict
    buckets = defaultdict(lambda: {"tis": [], "completed": [], "missed": []})
    for s in (daily_summaries or []):
        if not isinstance(s, dict):
            continue
        dt = _parse_dt_any(s.get('date'))
        if not dt:
            continue
        wd = dt.weekday()
        buckets[wd]["tis"].append(s.get('time_integrity_score') or 0)
        buckets[wd]["completed"].append(s.get('tasks_completed', 0) or 0)
        buckets[wd]["missed"].append(s.get('tasks_missed', 0) or 0)

    def _avg(xs):
        return round(sum(xs) / len(xs), 1) if xs else 0

    by_day = {}
    for wd in range(7):
        b = buckets.get(wd)
        if b and b["tis"]:
            by_day[wd] = {
                "avg_tis": int(round(_avg(b["tis"]))),
                "avg_completed": _avg(b["completed"]),
                "avg_missed": _avg(b["missed"]),
                "sample_size": len(b["tis"]),
            }
        else:
            by_day[wd] = {"avg_tis": None, "avg_completed": None,
                          "avg_missed": None, "sample_size": 0}

    eligible = {wd: d for wd, d in by_day.items() if d["sample_size"] >= 2}
    best_day = worst_day = best_name = worst_name = best_tis = worst_tis = None
    if eligible:
        best_day = max(eligible, key=lambda wd: eligible[wd]["avg_tis"])
        worst_day = min(eligible, key=lambda wd: eligible[wd]["avg_tis"])
        best_name, worst_name = _DOW_NAMES[best_day], _DOW_NAMES[worst_day]
        best_tis, worst_tis = eligible[best_day]["avg_tis"], eligible[worst_day]["avg_tis"]

    if best_name is None:
        rec = "Keep building history for pattern insights."
    else:
        rec = f"You execute best on {best_name}s."
        if worst_name and worst_name != best_name and worst_tis is not None and worst_tis < 65:
            rec += f" Keep {worst_name}s light."

    return {
        "by_day": by_day,
        "best_day": best_day,
        "best_day_name": best_name,
        "worst_day": worst_day,
        "worst_day_name": worst_name,
        "best_day_avg_tis": best_tis,
        "worst_day_avg_tis": worst_tis,
        "recommendation": rec,
    }


def ensure_daily_summaries(force=False):
    """Backfill/append daily summaries for completed days. Runs once per new day."""
    config = storage.load_config()
    today = datetime.now().strftime('%Y-%m-%d')
    if not force and config.get('last_summary_date') == today:
        return storage.load_daily_summaries()

    summaries = storage.load_daily_summaries()
    existing = {s.get('date') for s in summaries if isinstance(s, dict)}
    tasks = storage.load_tasks()

    dates = set()
    for t in tasks:
        for attr in ('completed_at', 'dropped_at', 'offloaded_at'):
            v = getattr(t, attr, None)
            if v:
                dates.add(v[:10])
    for e in _all_behavior_entries():
        ts = e.get('ts', '')
        if isinstance(ts, str) and len(ts) >= 10:
            dates.add(ts[:10])

    for d in sorted(dates):
        if d >= today or d in existing:
            continue
        summaries.append(compute_daily_summary(d, tasks, get_behavior_log_entries(d)))
        existing.add(d)

    summaries.sort(key=lambda s: s.get('date', ''))
    storage.save_daily_summaries(summaries)
    config['last_summary_date'] = today
    storage.save_config(config)
    recalc_streak()
    return summaries


def recalc_streak():
    """Consecutive days with >=1 completion (Seinfeld chain). Stored in config (Rule #6)."""
    config = storage.load_config()
    today = datetime.now().strftime('%Y-%m-%d')
    done_dates = {s['date'] for s in storage.load_daily_summaries()
                  if isinstance(s, dict) and (s.get('tasks_completed', 0) or 0) >= 1}
    tasks = storage.load_tasks()
    if any(t.completed and (getattr(t, 'completed_at', '') or '')[:10] == today for t in tasks):
        done_dates.add(today)

    streak = 0
    cur = datetime.now().date()
    if today not in done_dates:
        cur = cur - timedelta(days=1)
    while cur.strftime('%Y-%m-%d') in done_dates:
        streak += 1
        cur = cur - timedelta(days=1)

    config['execution_streak'] = streak
    config['streak_last_date'] = today
    storage.save_config(config)
    return streak


def check_momentum_warning():
    """Brainstorm #3 — gentle re-entry nudge after 2+ days with no completions."""
    tasks = storage.load_tasks()
    last = None
    for t in tasks:
        if t.completed and getattr(t, 'completed_at', None):
            d = t.completed_at[:10]
            if last is None or d > last:
                last = d
    if last is None:
        return
    last_dt = _parse_dt_any(last)
    if not last_dt:
        return
    gap = (datetime.now().date() - last_dt.date()).days
    if gap < 2:
        return
    pend = [t for t in tasks if not t.completed and not getattr(t, 'dropped_at', None)
            and not getattr(t, 'offloaded_at', None)]
    order = {'15m': 1, '30m': 2, '1h': 3, '2h': 4, '3h': 5, '4h+': 6}
    pend.sort(key=lambda t: order.get((t.duration or '').lower(), 3))
    print(f"{Fore.YELLOW}No completions in {gap} days. Small win today?{Style.RESET_ALL}")
    if pend:
        dur = f" [{pend[0].duration}]" if pend[0].duration else ""
        print(f"{Fore.CYAN}  → {pend[0].title}{dur}  ·  taskflow complete {pend[0].id}{Style.RESET_ALL}")


# ---- S12-D rendering helpers ----

def _tis_bar(score):
    filled = max(0, min(10, round((score or 0) / 10)))
    return "█" * filled + "░" * (10 - filled)


def _trend_arrow(trend):
    if trend == 'improving':
        return f"{Fore.GREEN}↑ improving{Style.RESET_ALL}"
    if trend == 'declining':
        return f"{Fore.RED}↓ declining{Style.RESET_ALL}"
    return f"{Fore.YELLOW}→ stable{Style.RESET_ALL}"


def _dow(date):
    dt = _parse_dt_any(date)
    return dt.strftime('%A') if dt else (date or "")


def _hour_range(h):
    if h is None:
        return "—"
    def lab(x):
        x %= 24
        ap = 'am' if x < 12 else 'pm'
        hh = x % 12
        return f"{12 if hh == 0 else hh}{ap}"
    return f"{lab(h)}–{lab(h + 1)}"


def _print_streak_line(config):
    streak = config.get('execution_streak', 0) or 0
    fire = " 🔥" if streak > 0 else ""
    print(f"  Streak: {Fore.YELLOW}{streak} day{'s' if streak != 1 else ''}{fire}{Style.RESET_ALL}")


def _today_summary_live():
    today = datetime.now().strftime('%Y-%m-%d')
    s = compute_daily_summary(today, storage.load_tasks(), get_behavior_log_entries(today))
    cfg = storage.load_config()
    s['path_adherence'] = cfg.get('path_adherence_today')
    return s


def render_stats_main():
    summaries = storage.load_daily_summaries()
    config = storage.load_config()
    bar = Fore.CYAN + ("━" * 44) + Style.RESET_ALL
    print()
    print(bar)
    print(f"{Fore.CYAN + Style.BRIGHT}⚡  PERFORMANCE TELEMETRY{Style.RESET_ALL}")
    print(bar)
    print()

    if len(summaries) < 3:
        print(f"{Fore.YELLOW}Building your execution profile…{Style.RESET_ALL}")
        print(f"{len(summaries)}/3 days of history. Keep using TaskFlow — stats populate automatically.")
        print()
        _print_streak_line(config)
        print(bar)
        return

    w = compute_weekly_stats(summaries)
    print("TIME INTEGRITY SCORE (7-day avg)")
    print(f"  {_tis_bar(w['avg_score'])}  {round(w['avg_score'])} / 100  {_trend_arrow(w['trend'])}")
    bd, wd = w['best_day'], w['worst_day']
    print(f"  Best day: {_dow(bd['date'])} ({bd['score']})  ·  Watch: {_dow(wd['date'])} ({wd['score']})")
    print()

    miss = sum(d.get('tasks_missed', 0) or 0 for d in w['days'])
    drop = sum(d.get('tasks_dropped', 0) or 0 for d in w['days'])
    dmet = sum(d.get('deadlines_met', 0) or 0 for d in w['days'])
    dmiss = sum(d.get('deadlines_missed', 0) or 0 for d in w['days'])
    hardw = w['hard_deadlines_missed_week']
    print("EXECUTION SUMMARY (this week)")
    print(f"  Completed: {w['total_completed']}  ·  Missed: {miss}  ·  Dropped: {drop}")
    hard_str = f"  ({Fore.RED}{hardw} HARD{Style.RESET_ALL})" if hardw else ""
    print(f"  Deadlines: {dmet} met  ·  {dmiss} missed{hard_str}")
    sessions = sum(d.get('focus_sessions', 0) or 0 for d in w['days'])
    print(f"  Focus time: {_fmt_minutes(w['total_focus_minutes'])} across {sessions} sessions")
    print()

    print("PATTERNS")
    ph = w['most_productive_hour']
    print(f"  Peak hour: {_hour_range(ph)}  (highest completion rate)" if ph is not None else "  Peak hour: —")
    if w['most_avoided_tag']:
        print(f"  {Fore.YELLOW}Watch out: #{w['most_avoided_tag']} tasks  (most avoided category){Style.RESET_ALL}")
    ad = w['avg_start_drift']
    if ad is not None:
        note = "you start late" if ad > 0 else "ahead of plan"
        print(f"  Avg start drift: {'+' if ad > 0 else ''}{round(ad)} min  ({note})")
    if config.get('path_adherence_today') is not None:
        print(f"  Path adherence: {round(config['path_adherence_today'] * 100)}%")
    print()

    print("MOMENTUM")
    _print_streak_line(config)
    # Brainstorm #6 — velocity (this-week vs prior-week tasks/day)
    all_sorted = sorted(summaries, key=lambda s: s.get('date', ''))
    this_wk = all_sorted[-7:]
    prev_wk = all_sorted[-14:-7]
    if this_wk:
        v_now = sum(d.get('tasks_completed', 0) or 0 for d in this_wk) / len(this_wk)
        line = f"  Velocity: {v_now:.1f} tasks/day"
        if prev_wk:
            v_prev = sum(d.get('tasks_completed', 0) or 0 for d in prev_wk) / len(prev_wk)
            arrow = "↑" if v_now > v_prev else ("↓" if v_now < v_prev else "→")
            line += f"  ({arrow} from {v_prev:.1f})"
        print(line)
    # Brainstorm #8 — focus effectiveness (tasks/day with vs without a focus session)
    wf = [d for d in summaries if (d.get('focus_sessions', 0) or 0) > 0]
    nf = [d for d in summaries if (d.get('focus_sessions', 0) or 0) == 0]
    if wf and nf:
        def _avg_done(lst):
            return sum(d.get('tasks_completed', 0) or 0 for d in lst) / len(lst)
        print(f"  Focus effect: {_avg_done(wf):.1f} done/day with focus  vs  {_avg_done(nf):.1f} without")
    if w['recovery_sessions']:
        succ = sum(1 for d in w['days'] if d.get('recovery_successful'))
        print(f"  Recovery: {w['recovery_sessions']} session(s) this week  ·  {succ} successful")
    print()
    print(bar)


def render_stats_today():
    s = _today_summary_live()
    bar = Fore.CYAN + ("━" * 44) + Style.RESET_ALL
    print(f"\n{bar}\n{Fore.CYAN + Style.BRIGHT}⚡  TODAY · {_dow(s['date'])}{Style.RESET_ALL}\n{bar}\n")
    print(f"  Time Integrity (partial): {_tis_bar(s['time_integrity_score'])}  {s['time_integrity_score']} / 100")
    print(f"  Completed: {s['tasks_completed']}  ·  Missed: {s['tasks_missed']}  ·  Postponed: {s['tasks_postponed']}")
    print(f"  Deadlines: {s['deadlines_met']} met  ·  {s['deadlines_missed']} missed")
    print(f"  Focus: {_fmt_minutes(s['focus_minutes_total'])} across {s['focus_sessions']} sessions")
    if s['best_hour'] is not None:
        print(f"  Most active hour: {_hour_range(s['best_hour'])}")
    print(f"\n{bar}")


def render_stats_week():
    """S14-D — calendar-week (Mon→Sun) breakdown. `—` for days with no summary yet (Rule #8)."""
    summaries = storage.load_daily_summaries()
    by_date = {s.get('date'): s for s in summaries if isinstance(s, dict)}
    now = datetime.now()
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    streak_dates = {s['date'] for s in summaries
                    if isinstance(s, dict) and (s.get('tasks_completed', 0) or 0) >= 1}

    bar = Fore.CYAN + ("━" * 44) + Style.RESET_ALL
    R = Style.RESET_ALL
    dim = Fore.WHITE + Style.DIM
    print(f"\n{bar}\n{Fore.CYAN + Style.BRIGHT}⚡  WEEKLY BREAKDOWN{R}\n{bar}\n")
    print(f"       {'Score':>5}  {'Done':>4}  {'Missed':>6}  {'Focus':>5}   Streak")

    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    have_data = []
    for i in range(7):
        d = (monday + timedelta(days=i)).strftime('%Y-%m-%d')
        s = by_date.get(d)
        if not s:
            print(f"{names[i]:<6} {dim}{'—':>5}  {'—':>4}  {'—':>6}  {'—':>5}{R}")
            continue
        sc = s.get('time_integrity_score') or 0
        col = Fore.GREEN if sc >= 80 else (Fore.YELLOW if sc >= 60 else Fore.RED)
        done = s.get('tasks_completed', 0) or 0
        missed = s.get('tasks_missed', 0) or 0
        focus = s.get('focus_sessions', 0) or 0
        fire = "🔥" if d in streak_dates else ""
        print(f"{names[i]:<6} {col}{sc:>5}{R}  {done:>4}  {missed:>6}  {focus:>5}   {fire}")
        have_data.append(s)

    print()
    if have_data:
        w = compute_weekly_stats(summaries) or {}
        avg = round(sum((s.get('time_integrity_score') or 0) for s in have_data) / len(have_data))
        print(f"7-day avg: {avg}  {_trend_arrow(w.get('trend', 'stable'))}")
        best = max(have_data, key=lambda s: s.get('time_integrity_score') or 0)
        worst = min(have_data, key=lambda s: s.get('time_integrity_score') or 0)
        print(f"Best: {_dow(best['date'])} ({best.get('time_integrity_score') or 0})"
              f"  ·  Watch: {_dow(worst['date'])} ({worst.get('time_integrity_score') or 0})")
    else:
        print(f"{dim}No data yet this week. Complete tasks to populate.{R}")
    print(bar)


def export_stats_csv():
    import csv
    summaries = storage.load_daily_summaries()
    if not summaries:
        print("No daily summaries to export yet.")
        return
    fname = f"taskflow_stats_{datetime.now().strftime('%Y%m%d')}.csv"
    cols = ["date", "tasks_completed", "tasks_missed", "tasks_postponed", "tasks_dropped",
            "tasks_offloaded", "focus_sessions", "focus_minutes_total", "deadlines_met",
            "deadlines_missed", "hard_deadlines_missed", "avg_start_drift_minutes",
            "recovery_activated", "recovery_successful", "path_adherence",
            "time_integrity_score", "best_hour", "worst_hour"]
    try:
        with open(fname, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for s in summaries:
                w.writerow({c: s.get(c) for c in cols})
        print(f"Exported {len(summaries)} day(s) → {fname}")
    except Exception as e:
        print(f"Export failed: {e}")


def render_stats_accuracy():
    """Brainstorm #5 — duration estimate accuracy from duration_accuracy_ratio."""
    tasks = [t for t in storage.load_tasks()
             if getattr(t, 'duration_accuracy_ratio', None) is not None]
    bar = Fore.CYAN + ("━" * 44) + Style.RESET_ALL
    print(f"\n{bar}\n{Fore.CYAN + Style.BRIGHT}⚡  DURATION ACCURACY{Style.RESET_ALL}\n{bar}\n")
    if len(tasks) < 3:
        print(f"{Fore.YELLOW}Building profile… complete a few timed tasks (focus + estimate) first.{Style.RESET_ALL}")
        print(bar)
        return
    ratios = [t.duration_accuracy_ratio for t in tasks]
    avg = sum(ratios) / len(ratios)
    pct = round((avg - 1) * 100)
    if pct > 0:
        print(f"  You underestimate by {pct}% on average (tasks run long).")
    elif pct < 0:
        print(f"  You overestimate by {abs(pct)}% on average (tasks finish early).")
    else:
        print("  Your estimates are spot-on on average.")
    # worst tag
    from collections import defaultdict
    tagsum = defaultdict(list)
    for t in tasks:
        for tag in (t.tags or []):
            if tag.lower() != 'inbox':
                tagsum[tag].append(t.duration_accuracy_ratio)
    worst = None
    for tag, rs in tagsum.items():
        m = sum(rs) / len(rs)
        if worst is None or m > worst[1]:
            worst = (tag, m)
    if worst and worst[1] > 1.05:
        print(f"  Worst category: #{worst[0]} (+{round((worst[1] - 1) * 100)}% over estimate)")
    print(f"\n{bar}")


def render_stats_tags():
    """Brainstorm #4 — completion rate by tag."""
    tasks = storage.load_tasks()
    from collections import defaultdict
    tot = defaultdict(int)
    done = defaultdict(int)
    for t in tasks:
        for tag in (t.tags or []):
            if tag.lower() == 'inbox':
                continue
            tot[tag] += 1
            if t.completed:
                done[tag] += 1
    bar = Fore.CYAN + ("━" * 44) + Style.RESET_ALL
    print(f"\n{bar}\n{Fore.CYAN + Style.BRIGHT}⚡  PERFORMANCE BY CATEGORY{Style.RESET_ALL}\n{bar}\n")
    if not tot:
        print(f"{Fore.YELLOW}No tagged tasks yet. Tag tasks to see category performance.{Style.RESET_ALL}")
        print(bar)
        return
    for tag in sorted(tot, key=lambda k: done[k] / max(1, tot[k]), reverse=True):
        rate = round(done[tag] / max(1, tot[tag]) * 100)
        col = Fore.GREEN if rate >= 70 else (Fore.YELLOW if rate >= 40 else Fore.RED)
        print(f"  #{tag:<16} {col}{rate:>3}%{Style.RESET_ALL}  ({done[tag]}/{tot[tag]})")
    print(f"\n{bar}")


def render_heatmap():
    """Brainstorm #2 — ASCII completion heatmap by hour, last 30 days."""
    from collections import Counter
    cutoff = (datetime.now() - timedelta(days=30)).date()
    by_hour = Counter()
    for e in _all_behavior_entries():
        if e.get('event') == 'task_completed':
            dt = _parse_dt_any(e.get('ts'))
            if dt and dt.date() >= cutoff:
                by_hour[dt.hour] += 1
    bar = Fore.CYAN + ("━" * 52) + Style.RESET_ALL
    print(f"\n{bar}\n{Fore.CYAN + Style.BRIGHT}⚡  PRODUCTIVITY HEATMAP · last 30 days{Style.RESET_ALL}\n{bar}\n")
    if not by_hour:
        print(f"{Fore.YELLOW}No completion history yet. Complete tasks to build the map.{Style.RESET_ALL}")
        print(bar)
        return
    peak = max(by_hour.values())
    blocks = " ▁▂▃▄▅▆▇█"
    # show 6:00 → 23:00 (waking hours), then any off-hours with activity
    for h in range(6, 24):
        n = by_hour.get(h, 0)
        lvl = 0 if n == 0 else max(1, round(n / peak * (len(blocks) - 1)))
        col = Fore.GREEN if n >= peak * 0.66 else (Fore.YELLOW if n > 0 else Fore.WHITE + Style.DIM)
        print(f"  {_hour_range(h):<10} {col}{blocks[lvl] * 12}{Style.RESET_ALL} {n}")
    print(f"\n{bar}")


def command_rescue():
    """Brainstorm #9 — best high-impact task completable in ~30 minutes."""
    tasks = [t for t in storage.load_tasks()
             if not t.completed and not getattr(t, 'dropped_at', None) and not getattr(t, 'offloaded_at', None)]
    short = [t for t in tasks if (t.duration or '').lower() in ('15m', '30m')]
    pool = short or [t for t in tasks if not t.duration] or tasks
    if not pool:
        print(f"\n{Fore.WHITE}Nothing to rescue — your board is clear.{Style.RESET_ALL}\n")
        return

    def rank(t):
        score = score_for_path(t)
        if getattr(t, 'deadline', None):
            score += 25
        if (t.duration or '').lower() in ('15m', '30m'):
            score += 15
        return score

    best = max(pool, key=rank)
    bar = Fore.CYAN + ("━" * 44) + Style.RESET_ALL
    print(f"\n{bar}\n{Fore.CYAN + Style.BRIGHT}⚡  RESCUE MISSION{Style.RESET_ALL}\n{bar}\n")
    dur = f" [{best.duration}]" if best.duration else ""
    print(f"  Your best 30-minute win right now:\n")
    print(f"  {_path_prio_color(best)}→ {best.title}{Style.RESET_ALL}{dur}  ·  {best.priority}")
    due = _due_phrase(best)
    if due:
        print(f"    {Fore.WHITE + Style.DIM}Due: {due}{Style.RESET_ALL}")
    print(f"\n  Start: {Fore.CYAN}taskflow complete {best.id}{Style.RESET_ALL}  when done.")
    print(f"\n{bar}")


def maybe_weekly_review():
    """S14-A/E — Monday-morning weekly review prompt, once per week.

    Fires Monday before 14:00, at most once per week. The week key is strftime('%Y-W%W')
    used CONSISTENTLY for both the write and the compare (Rule #7) — a mismatched format here
    previously caused it to fire every day, so write and read must stay identical.
    """
    now = datetime.now()
    if now.weekday() != 0 or now.hour >= 14:
        return
    config = storage.load_config()
    week_str = now.strftime('%Y-W%W')
    if config.get('last_weekly_review') == week_str:
        return
    summaries = storage.load_daily_summaries()
    if len(summaries) < 3:
        config['last_weekly_review'] = week_str
        storage.save_config(config)
        return

    w = compute_weekly_stats(summaries)
    dow = compute_day_of_week_stats(summaries)
    week_days = w.get('days', []) if w else []
    R = Style.RESET_ALL

    # biggest win = the day with the most completions this week
    win_day, win_n = None, -1
    for d in week_days:
        c = d.get('tasks_completed', 0) or 0
        if c >= win_n:
            win_n, win_day = c, d
    # most-avoided tag + how many times it was deferred this week
    avoided = w.get('most_avoided_tag') if w else None
    avoided_n = 0
    if avoided:
        cutoff = (now - timedelta(days=7)).strftime('%Y-%m-%d')
        for t in storage.load_tasks():
            if avoided in (t.tags or []):
                pc = getattr(t, 'postpone_count', 0) or 0
                dropped_recent = getattr(t, 'dropped_at', None) and t.dropped_at[:10] >= cutoff
                if pc >= 1 or dropped_recent:
                    avoided_n += pc or 1

    avg_score = round(w['avg_score']) if w else 0
    sc_col = Fore.GREEN if avg_score >= 70 else (Fore.YELLOW if avg_score >= 50 else Fore.RED)

    bar = Fore.CYAN + ("━" * 44) + Style.RESET_ALL
    print()
    print(bar)
    print(f"{Fore.CYAN + Style.BRIGHT}📊  WEEKLY REVIEW · Week of {now.strftime('%d %b').replace(' 0', ' ')}{R}")
    print(bar)
    print(f"Last week: Time Integrity Score  {sc_col}{avg_score}{R} / 100  {_trend_arrow(w['trend'])}\n")

    if win_day is not None:
        print(f"Your biggest win:   {_dow(win_day.get('date'))} — {win_n} task{'s' if win_n != 1 else ''}")
    wd = w['worst_day']
    print(f"Your toughest day:  {_dow(wd['date'])} (score: {wd['score']})")
    if avoided:
        print(f"Your avoidance:     #{avoided} deferred {avoided_n}×")
    print()

    # S14-E: day-of-week pattern insight (only with >=3 samples for that weekday)
    bd_wd = dow.get('best_day')
    if bd_wd is not None and dow['by_day'][bd_wd]['sample_size'] >= 3:
        print(f"{Fore.CYAN}Pattern:  You execute best on {dow['best_day_name']}s (avg: {dow['best_day_avg_tis']}){R}")
        ws_wd = dow.get('worst_day')
        if (ws_wd is not None and ws_wd != bd_wd and dow['by_day'][ws_wd]['sample_size'] >= 3
                and dow['worst_day_avg_tis'] is not None and dow['worst_day_avg_tis'] < 65):
            print(f"{Fore.YELLOW}Watch out: {dow['worst_day_name']}s have been tough (avg: {dow['worst_day_avg_tis']}){R}")
        print()

    print(f"{Fore.WHITE + Style.BRIGHT}This week, consider:{R}")
    today_wd, tomorrow_wd = now.weekday(), (now.weekday() + 1) % 7
    if bd_wd is not None and bd_wd == today_wd:
        sugg = "Today is your strongest day. Load it heavy."
    elif bd_wd is not None and bd_wd == tomorrow_wd:
        sugg = "Tomorrow is your best day. Save hard work for it."
    elif avoided:
        sugg = f"Schedule #{avoided} tasks earlier in the day."
    else:
        sugg = "Complete at least one task to maintain your streak."
    print(f"{Fore.CYAN}→ {sugg}{R}")
    print(bar)
    print(f"{Fore.WHITE + Style.DIM}Ready? [Enter to continue · Q to skip]{R}")
    try:
        choice = get_valid_input("", "")
    except Exception:
        choice = ""
    config['last_weekly_review'] = week_str
    storage.save_config(config)
    if (choice or "").strip().lower() == 'q':
        return


def run_today_view():
    """Show today's tasks chronologically with Now Window."""
    tasks = storage.load_tasks()
    timeline = storage.load_timeline()
    config = storage.load_config()
    
    # S4-G: Update today view opened counts
    config["today_views_opened"] = config.get("today_views_opened", 0) + 1
    config["last_today_view"] = datetime.now().isoformat()
    storage.save_config(config)
    
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    
    completed_today = []
    main_tasks = []
    
    for task in tasks:
        # Completed today section
        if task.completed:
            if task.completed_at and task.completed_at.startswith(today_str):
                completed_today.append(task)
            continue
            
        # Exclude dropped/offloaded from main list
        if getattr(task, 'dropped_at', None) or getattr(task, 'offloaded_at', None):
            continue
        if getattr(task, 'status', None) in ['dropped', 'offloaded']:
            continue
            
        included = False
        task_dt = None
        
        # (a) deadline date is today
        if task.deadline:
            try:
                dt = datetime.fromisoformat(task.deadline)
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                if dt.strftime('%Y-%m-%d') == today_str:
                    included = True
                    task_dt = dt
            except ValueError:
                pass
                
        # (b) scheduled date is today
        if not included:
            tslot = timeline.get(str(task.id))
            if tslot and tslot.startswith(today_str):
                included = True
                # If there's a custom slot like YYYY-MM-DD HH:MM, we can parse it to dt
                if len(tslot) >= 16:
                    try:
                        slot_dt = datetime.fromisoformat(tslot)
                        if slot_dt.tzinfo is not None:
                            slot_dt = slot_dt.replace(tzinfo=None)
                        task_dt = slot_dt
                    except ValueError:
                        pass
            elif task.scheduled_date == today_str:
                included = True
                
        # (c) prime date is today
        if not included:
            tslot = timeline.get(str(task.id))
            if tslot == f"{today_str}_prime":
                included = True
            elif task.prime_target_date == today_str:
                included = True
                
        # (d) untimed, "todo" status, and created today
        if not included and not task.deadline:
            if task.created_at and task.created_at.startswith(today_str):
                included = True
                
        if included:
            main_tasks.append((task, task_dt))
            
    if not main_tasks and not completed_today:
        print("\nNo missions scheduled for today.\nAdd one: taskflow add\n")
        return
        
    timed_tasks = [t for t in main_tasks if t[1] is not None]
    untimed_tasks = [t for t in main_tasks if t[1] is None]
    
    timed_tasks.sort(key=lambda t: t[1])
    
    priority_order = {"critical": 0, "strategic": 1, "noise": 2, "purge": 3, "high": 0, "medium": 1, "low": 2}
    untimed_tasks.sort(key=lambda t: priority_order.get((t[0].priority or "").lower(), 1))
    
    # Increment today_view_shown_count for all tasks shown and save
    for task, _ in timed_tasks:
        task.today_view_shown_count += 1
    for task, _ in untimed_tasks:
        task.today_view_shown_count += 1
    for task in completed_today:
        task.today_view_shown_count += 1
    storage.save_tasks(tasks)
    
    # Calculate Now window
    window_start = now - timedelta(minutes=45)
    window_end = now + timedelta(minutes=45)
    
    window_tasks = [t for t in timed_tasks if window_start <= t[1] <= window_end]
    primary_now_task = window_tasks[0] if window_tasks else None
    secondary_window_tasks = window_tasks[1:]
    
    next_task = None
    if not primary_now_task:
        for task, dt in timed_tasks:
            if dt > now:
                next_task = (task, dt)
                break
                
    # Calculate pressure counts for Approaching header
    pressure_counts = {2: 0, 3: 0}
    for task, _ in main_tasks:
        p_level = get_pressure_level(task)
        if p_level in [2, 3]:
            pressure_counts[p_level] += 1
                
    total_pressure_tasks = pressure_counts[2] + pressure_counts[3]
    print()
    if total_pressure_tasks > 0:
        if pressure_counts[3] > 0:
            header_color = Fore.RED + Style.BRIGHT
            print(header_color + f"  ⚡ {total_pressure_tasks} task(s) need immediate attention." + Style.RESET_ALL)
        else:
            header_color = Fore.YELLOW
            print(header_color + f"  ⚡ {total_pressure_tasks} task(s) need attention soon." + Style.RESET_ALL)
        
    # S4-G: Telemetry behavior logging with complete schema
    now_window_task_id = primary_now_task[0].id if primary_now_task else None
    log_behavior({
        "event": "today_view_opened",
        "task_count": len(main_tasks),
        "now_window_task_id": now_window_task_id,
        "pressure_tasks": total_pressure_tasks
    })
    
    # S4-E: Dividers pad to exactly 50 characters
    header_str = f" TODAY · {now.strftime('%A, %B %d').replace(' 0', ' ')} "
    header_str = header_str.replace(", 0", ", ")
    divider = f"──{header_str}"
    divider += "─" * (50 - len(divider))
    print(Fore.WHITE + Style.DIM + divider + Style.RESET_ALL)
    print()
    
    for task, dt in timed_tasks:
        time_str = f"[{dt.strftime('%H:%M')}]"
        
        row_color = Fore.WHITE
        prefix = "   "
        suffix = ""
        is_now = False
        is_next = False
        is_window = False
        
        pressure_line = ""
        
        if primary_now_task and task.id == primary_now_task[0].id:
            row_color = Fore.WHITE + Style.BRIGHT
            prefix = "▶  "
            suffix = f"   {Fore.CYAN}[NOW ← you are here]{Style.RESET_ALL}"
            is_now = True
        elif task.id in [t[0].id for t in secondary_window_tasks]:
            row_color = Fore.WHITE + Style.BRIGHT
            prefix = "▶  "
            suffix = f"   {Fore.CYAN}[WINDOW]{Style.RESET_ALL}"
            is_window = True
        elif next_task and task.id == next_task[0].id:
            row_color = Fore.WHITE + Style.BRIGHT
            prefix = "·  " # S4-D prefix marker
            suffix = f"   {Fore.CYAN}[NEXT MISSION]{Style.RESET_ALL}"
            is_next = True
            
        p_level = get_pressure_level(task)
        if p_level > 0:
            td = dt - now
            rem_str = format_time_remaining(td, dt)
            if p_level == 3:
                if getattr(task, 'deadline_type', None) == "hard":
                    row_color = Fore.RED + Style.BRIGHT
                else:
                    row_color = Fore.YELLOW + Style.BRIGHT
                if td.total_seconds() < 0:
                    suffix += f" · {Fore.RED + Style.BRIGHT}{rem_str}{Style.RESET_ALL}"
                else:
                    suffix += f" · {Fore.RED + Style.BRIGHT}{rem_str} ⚠{Style.RESET_ALL}"
                
                mins = int(td.total_seconds() // 60)
                rem_spelled = f"{mins} minutes" if mins >= 0 else f"{abs(mins)} minutes ago"
                pressure_line = f"\n     ··· {Fore.RED + Style.BRIGHT}⚠ Execution window closing in {rem_spelled}.{Style.RESET_ALL}"
            elif p_level == 2:
                row_color = Fore.YELLOW
                suffix += f" · {Fore.YELLOW + Style.BRIGHT}{rem_str}{Style.RESET_ALL}"
                
                mins = int(td.total_seconds() // 60)
                rem_spelled = f"{mins} minutes"
                pressure_line = f"\n     ··· {Fore.YELLOW}Execution window closing in {rem_spelled}.{Style.RESET_ALL}"
            elif p_level == 1:
                suffix += f" · {Fore.YELLOW}{rem_str}{Style.RESET_ALL}"
        
        if task.postpone_count >= 5:
            suffix += f"  {Fore.RED}(postponed ×{task.postpone_count}) ⚠⚠{Style.RESET_ALL}"
        elif task.postpone_count >= 3:
            suffix += f"  {Fore.YELLOW}(postponed ×{task.postpone_count}) ⚠{Style.RESET_ALL}"
        elif task.postpone_count == 2:
            suffix += f"  {Fore.YELLOW}(postponed ×2){Style.RESET_ALL}"
            
        dur_display = f"  [{task.duration}] " if task.duration else ""
        
        if dt > now:
            rem_str = format_time_remaining(dt - now, dt)
            suffix += f"  ← {rem_str}"
        else:
            rem_str = format_time_remaining(dt - now, dt)
            suffix += f"  ← {rem_str}"

        if getattr(task, 'deadline_type', None) == "hard":
            suffix = f"  {Fore.RED}[HARD]{Style.RESET_ALL}" + suffix
            
        # S4-E Brackets around time stamp
        print(row_color + f"{prefix}{time_str}  {task.title:<26}{Style.RESET_ALL}{dur_display}{suffix}")
        
        if is_now or is_next or is_window:
            if is_next:
                if task.duration:
                    ends_part = ""
                    try:
                        dur_str = task.duration.lower()
                        import re
                        m = re.match(r'(\d+)(m|h)', dur_str)
                        if m:
                            val = int(m.group(1))
                            unit = m.group(2)
                            mins = val if unit == 'm' else val * 60
                            end_time = now + timedelta(minutes=mins)
                            ends_part = f" · Ends ~{end_time.strftime('%I:%M %p').lstrip('0')}"
                    except:
                        pass
                    print(row_color + f"           Est. duration: {task.duration}{ends_part}" + Style.RESET_ALL)
            else:
                tags_part = f" · #{', #'.join(task.tags)}" if task.tags else ""
                print(row_color + f"           Priority: {task.priority}{tags_part}" + Style.RESET_ALL)

        # E9: enrichment context — shown ONLY for the NOW task
        if is_now:
            now_desc = getattr(task, 'description', None)
            if now_desc:
                first_line = now_desc.split('\n')[0]
                if len(first_line) > 60:
                    first_line = first_line[:57] + "..."
                print(f"     {Style.DIM}··· {first_line}{Style.RESET_ALL}")
            now_links = getattr(task, 'links', None) or []
            if now_links:
                print(f"     {Style.DIM}··· 🔗 {len(now_links)} links — run: taskflow link {task.id} to access{Style.RESET_ALL}")
            now_chk = getattr(task, 'checklist', None) or []
            if now_chk:
                done_ct = sum(1 for x in now_chk if x.get('done'))
                print(f"     {Style.DIM}··· ☑ {done_ct}/{len(now_chk)} checklist — run: taskflow check {task.id}{Style.RESET_ALL}")

        if pressure_line:
            print(pressure_line)
            
    if untimed_tasks:
        print("\n  No time set:")
        for task, _ in untimed_tasks:
            priority_tags = f"{task.priority}"
            if task.tags:
                priority_tags += f" · #{', #'.join(task.tags)}"
                
            suffix = ""
            p_level = get_pressure_level(task)
            pressure_line = ""
            
            if p_level > 0 and task.deadline:
                try:
                    _dl = datetime.fromisoformat(task.deadline)
                    if _dl.tzinfo is not None:
                        _dl = _dl.replace(tzinfo=None)
                    td = _dl - now
                    rem_str = format_time_remaining(td, _dl)
                    if p_level == 3:
                        if td.total_seconds() < 0:
                            suffix += f" · {Fore.RED + Style.BRIGHT}{rem_str}{Style.RESET_ALL}"
                        else:
                            suffix += f" · {Fore.RED + Style.BRIGHT}{rem_str} ⚠{Style.RESET_ALL}"
                        mins = int(td.total_seconds() // 60)
                        rem_spelled = f"{mins} minutes" if mins >= 0 else f"{abs(mins)} minutes ago"
                        pressure_line = f"\n        ··· {Fore.RED + Style.BRIGHT}⚠ Execution window closing in {rem_spelled}.{Style.RESET_ALL}"
                    elif p_level == 2:
                        suffix += f" · {Fore.YELLOW + Style.BRIGHT}{rem_str}{Style.RESET_ALL}"
                        mins = int(td.total_seconds() // 60)
                        rem_spelled = f"{mins} minutes"
                        pressure_line = f"\n        ··· {Fore.YELLOW}Execution window closing in {rem_spelled}.{Style.RESET_ALL}"
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
                
    if completed_today:
        comp_hdr = "── COMPLETED TODAY "
        comp_hdr += "─" * (50 - len(comp_hdr))
        print("\n" + Fore.WHITE + Style.DIM + comp_hdr + Style.RESET_ALL)
        for task in completed_today:
            comp_time = "     "
            done_suffix = "done"
            if getattr(task, 'completed_at', None):
                try:
                    cdt = datetime.fromisoformat(task.completed_at)
                    if cdt.tzinfo is not None:
                        cdt = cdt.replace(tzinfo=None)
                    comp_time = cdt.strftime('%H:%M')
                    
                    if getattr(task, 'actual_start_time', None):
                        sdt = datetime.fromisoformat(task.actual_start_time)
                        if sdt.tzinfo is not None:
                            sdt = sdt.replace(tzinfo=None)
                        elapsed_hours = (cdt - sdt).total_seconds() / 3600.0
                        done_suffix = f"done · {round(elapsed_hours, 1)}h"
                    elif getattr(task, 'duration', None):
                        done_suffix = f"done · {task.duration}"
                except Exception:
                    pass
            print(Fore.WHITE + Style.DIM + f"     ✓  [{comp_time} completed]  {task.title:<26}  [{done_suffix}]{Style.RESET_ALL}")
            
    print(Fore.WHITE + Style.DIM + "─" * 50 + Style.RESET_ALL)
    
    target = primary_now_task or next_task
    if target:
        t, dt = target
        title_color = Fore.CYAN + Style.BRIGHT
        if primary_now_task:
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
        # S4-F edge cases (no NOW task and no upcoming timed task)
        if not timed_tasks and not untimed_tasks and completed_today:
            # Everything scheduled for today is done
            print(Fore.GREEN + Style.BRIGHT + "All missions complete. Excellent execution today. ✓" + Style.RESET_ALL)
        elif timed_tasks:
            # All scheduled windows have already passed
            print(Fore.YELLOW + "All scheduled windows have passed." + Style.RESET_ALL)
            print(Fore.YELLOW + "Consider: taskflow recover" + Style.RESET_ALL)
        elif untimed_tasks:
            # Only no-deadline tasks remain — surface the highest-priority one
            nt = untimed_tasks[0][0]
            print(Fore.CYAN + Style.BRIGHT + f"Next mission: {nt.title}" + Style.RESET_ALL)
    # S10-D: pointer to the full Daily Execution Path (one line, not the path itself)
    print()
    print(Fore.WHITE + Style.DIM + "─" * 50 + Style.RESET_ALL)
    print(f"  Execution path: {Fore.CYAN}taskflow path{Style.RESET_ALL}")
    print(Fore.WHITE + Style.DIM + "─" * 50 + Style.RESET_ALL)

    print()
    print_today_missed_notice(tasks)  # PASSIVE bottom notice — never prompts (see: taskflow missed)


# =========================================================
# FEATURE 9: RECOVERY MODE
# =========================================================

def _recovery_pending(t) -> bool:
    """A task is pending (eligible for recovery) if not completed/dropped/offloaded."""
    if t.completed or getattr(t, 'dropped_at', None) or getattr(t, 'offloaded_at', None):
        return False
    if getattr(t, 'status', None) in ['completed', 'done', 'dropped', 'offloaded']:
        return False
    return True


def _task_deadline_dt(t):
    """Parse a task deadline to a naive datetime, or None."""
    if not getattr(t, 'deadline', None):
        return None
    try:
        dt = datetime.fromisoformat(t.deadline)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except (ValueError, TypeError):
        return None


def should_trigger_recovery(tasks=None) -> bool:
    """S9-B: decide if the day has collapsed. Also auto-clears stale recovery state."""
    if tasks is None:
        tasks = storage.load_tasks()
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    state = storage.load_recovery_state()

    # Auto-clear stale recovery state when a new day starts
    if state.get('last_checked_date') != today_str:
        if state.get('active'):
            state['active'] = False
            state['dismissed_at'] = now.isoformat()
            _append_recovery_log(state)
            print(Fore.GREEN + Style.DIM + "New day. Recovery Mode cleared." + Style.RESET_ALL)
        state['last_checked_date'] = today_str
        storage.save_recovery_state(state)
        state = storage.load_recovery_state()

    if state.get('active'):
        return False  # already in recovery — don't re-trigger

    # Today's past-due pending tasks
    past_today = []
    for t in tasks:
        if not _recovery_pending(t):
            continue
        dt = _task_deadline_dt(t)
        if dt and dt.strftime('%Y-%m-%d') == today_str and dt < now:
            past_today.append((t, dt))

    # Condition A: 3+ missed today
    if len(past_today) >= 3:
        return True

    # Condition B: any HARD deadline missed today
    if any(getattr(t, 'deadline_type', None) == 'hard' for t, _ in past_today):
        return True

    # Condition C: 2+ morning (06:00–12:00) tasks today, all past, none completed
    morning_today = []
    for t in tasks:
        dt = _task_deadline_dt(t)
        if dt and dt.strftime('%Y-%m-%d') == today_str and 6 <= dt.hour < 12:
            morning_today.append((t, dt))
    if len(morning_today) >= 2:
        all_past = all(dt < now for _, dt in morning_today)
        none_completed = all(_recovery_pending(t) for t, _ in morning_today)
        if all_past and none_completed:
            return True

    return False


def select_recovery_tasks(tasks=None) -> List[Task]:
    """S9-C: score tasks and return the top 1–2 to salvage the day."""
    if tasks is None:
        tasks = storage.load_tasks()
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')

    candidates = [t for t in tasks if _recovery_pending(t)]
    scored = []
    for t in candidates:
        score = 0
        dt = _task_deadline_dt(t)
        is_today = bool(dt and dt.strftime('%Y-%m-%d') == today_str)
        if getattr(t, 'deadline_type', None) == 'hard' and is_today:
            score += 100
        if (t.priority or "").lower() in ["critical", "high"]:
            score += 50
        if dt and abs((dt - now).total_seconds()) <= 7200:   # within 2 hours either side
            score += 30
        if getattr(t, 'duration', None) in ["15m", "30m"]:
            score += 20
        if getattr(t, 'postpone_count', 0) >= 2:
            score -= 10
        scored.append((score, t))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored[:2]]


def _append_recovery_log(state):
    """Append a recovery session record (S9-A schema) to recovery_log.json.

    D2-02: reconcile against live tasks so a session task completed via plain
    `taskflow complete` (not the in-view [C]) still counts toward was_successful.
    """
    session = state.get('session_tasks', []) or []
    done = set(state.get('completed_in_recovery', []) or [])
    try:
        for t in storage.load_tasks():
            if t.id in session and t.completed:
                done.add(t.id)
    except Exception:
        pass
    comp = sorted(done)
    storage.append_recovery_log({
        "date": datetime.now().strftime('%Y-%m-%d'),
        "triggered_at": state.get('triggered_at'),
        "trigger_reason": state.get('trigger_reason'),
        "session_tasks": session,
        "tasks_completed": len(comp),
        "was_successful": len(comp) >= 1,
        "exited_at": datetime.now().isoformat()
    })


def _recovery_pressure_color(task):
    p = get_pressure_level(task)
    if p >= 3:
        return Fore.RED + Style.BRIGHT
    if p == 2:
        return Fore.YELLOW + Style.BRIGHT
    if p == 1:
        return Fore.YELLOW
    return Fore.CYAN


def _recovery_render(recovery_tasks, focus_idx):
    R = Style.RESET_ALL
    bar = Fore.YELLOW + "━" * 40 + R
    print()
    print(bar)
    print(Fore.YELLOW + Style.BRIGHT + "⚡  RECOVERY MODE" + R)
    print(bar)
    print(Fore.WHITE + "Today's been rough. Let's salvage what matters." + R)
    print(bar)
    print()
    print(f"Your {len(recovery_tasks)} remaining mission(s):")
    print()
    for idx, t in enumerate(recovery_tasks, 1):
        dtype = getattr(t, 'deadline_type', None) or 'soft'
        dur = t.duration or 'no est.'
        marker = "▶" if (idx - 1) == focus_idx else " "
        print(f"  {marker} {idx}.  " + Fore.WHITE + Style.BRIGHT + f"{t.title}" + R + f"   {Fore.CYAN}[{t.priority} · {dtype} · {dur}]{R}")
        dt = _task_deadline_dt(t)
        if dt:
            rem = format_time_remaining(dt - datetime.now(), dt)
            print(f"      {_recovery_pressure_color(t)}Due: {dt.strftime('%a %d %b at %I:%M %p')} · {rem}{R}")
    print()
    print(bar)
    print(Fore.WHITE + Style.DIM + "Everything else is paused. Focus on these." + R)
    print(bar)
    print()
    fnum = focus_idx + 1
    print(f"  {Fore.CYAN}[F]{R} Start focus on mission {fnum}")
    print(f"  {Fore.CYAN}[C]{R} Mark mission {fnum} as complete")
    if len(recovery_tasks) > 1:
        print(f"  {Fore.CYAN}[N]{R} View next mission")
    print(f"  {Fore.CYAN}[A]{R} Show all tasks anyway")
    print(f"  {Fore.CYAN}[X]{R} Exit recovery mode")


def _recovery_complete(task_id):
    """Complete a task within recovery and record it in completed_in_recovery."""
    complete_task(task_id)
    state = storage.load_recovery_state()
    comp = state.get('completed_in_recovery', []) or []
    if task_id not in comp:
        comp.append(task_id)
    state['completed_in_recovery'] = comp
    storage.save_recovery_state(state)


def _recovery_auto_exit(state):
    """S9-H: every session task is done — exit and celebrate."""
    state['active'] = False
    state['dismissed_at'] = datetime.now().isoformat()
    _append_recovery_log(state)
    storage.save_recovery_state(state)
    R = Style.RESET_ALL
    bar = Fore.GREEN + "━" * 40 + R
    n = len(state.get('completed_in_recovery', []) or [])
    print()
    print(bar)
    print(Fore.GREEN + Style.BRIGHT + "✓  RECOVERY COMPLETE" + R)
    print(bar)
    print(Fore.WHITE + "You saved the day." + R)
    print(Fore.WHITE + f"Completed in recovery: {n}" + R)
    print(bar)


def run_recovery_view():
    """S9-E/F/H: interactive Recovery Mode dashboard. Never traps — [X] always exits."""
    focus_idx = 0
    while True:
        state = storage.load_recovery_state()
        if not state.get('active'):
            return
        tasks = storage.load_tasks()
        session_ids = state.get('session_tasks', []) or []
        recovery_tasks = [t for t in tasks if t.id in session_ids and _recovery_pending(t)]

        if not recovery_tasks:
            _recovery_auto_exit(state)
            return

        if focus_idx >= len(recovery_tasks):
            focus_idx = 0

        _recovery_render(recovery_tasks, focus_idx)
        choice = get_valid_input("  Choice: ").strip().upper()
        target = recovery_tasks[focus_idx]
        R = Style.RESET_ALL

        if choice == 'F':
            target.actual_start_time = datetime.now().isoformat()
            storage.save_tasks(tasks)
            print(Fore.CYAN + f"\nStarting focus: {target.title}" + R)
            print(Fore.CYAN + f"Run: taskflow focus --id {target.id} to begin." + R)
        elif choice == 'C':
            confirm = get_valid_input(f"Mark '{target.title}' complete? [Y/n]: ", "y").strip().lower()
            if confirm in ('y', ''):
                _recovery_complete(target.id)
                print(Fore.GREEN + Style.BRIGHT + "Mission complete." + R)
                focus_idx = 0
            # loop re-renders remaining (or auto-exits when none remain)
        elif choice == 'N':
            if len(recovery_tasks) > 1:
                focus_idx = (focus_idx + 1) % len(recovery_tasks)
            else:
                print(Fore.WHITE + Style.DIM + "Only one mission. Stay on it." + R)
        elif choice == 'A':
            print(Fore.YELLOW + "\nShowing all tasks. Recovery Mode still active." + R)
            list_tasks()
            return
        elif choice == 'X':
            confirm = get_valid_input("Exit Recovery Mode? [Y/n]: ", "y").strip().lower()
            if confirm in ('y', ''):
                state['active'] = False
                state['dismissed_at'] = datetime.now().isoformat()
                _append_recovery_log(state)
                storage.save_recovery_state(state)
                print(Fore.WHITE + Style.DIM + "Recovery Mode exited. You're on your own now." + R)
                return
            print(Fore.CYAN + "Good call. Stay focused." + R)
        else:
            # Unrecognized input — avoid trapping in non-interactive contexts
            return


def command_recover(trigger: bool = False, exit_mode: bool = False, status: bool = False):
    """S9-I: handle the recover command (default trigger / --exit / --status)."""
    R = Style.RESET_ALL
    state = storage.load_recovery_state()

    if status:
        if state.get('active'):
            since = "recently"
            try:
                tdt = datetime.fromisoformat(state.get('triggered_at'))
                mins = int((datetime.now() - tdt).total_seconds() / 60)
                since = f"{mins} min ago" if mins < 120 else f"{mins // 60}h ago"
            except Exception:
                pass
            tasks = storage.load_tasks()
            remaining = len([t for t in tasks if t.id in (state.get('session_tasks') or []) and _recovery_pending(t)])
            print(Fore.YELLOW + f"Recovery Mode active since {since}. {remaining} mission(s) remaining." + R)
        else:
            print(Fore.WHITE + Style.DIM + "Recovery Mode is not active." + R)
        return

    if exit_mode:
        if not state.get('active'):
            print("Recovery Mode is not active.")
            return
        state['active'] = False
        state['dismissed_at'] = datetime.now().isoformat()
        _append_recovery_log(state)
        storage.save_recovery_state(state)
        print(Fore.WHITE + Style.DIM + "Recovery Mode exited. You're on your own now." + R)
        return

    # Default / --trigger: show view if active, else manually engage (reason "D")
    if state.get('active'):
        run_recovery_view()
        return

    recovery_tasks = select_recovery_tasks()
    if not recovery_tasks:
        print(Fore.GREEN + "No actionable tasks. Recovery complete." + R)
        return
    state['active'] = True
    state['triggered_at'] = datetime.now().isoformat()
    state['trigger_reason'] = "D"
    state['session_tasks'] = [t.id for t in recovery_tasks]
    state['completed_in_recovery'] = []
    state['dismissed_at'] = None
    state['last_checked_date'] = datetime.now().strftime('%Y-%m-%d')
    storage.save_recovery_state(state)
    run_recovery_view()


def check_recovery_mode() -> bool:
    """Auto-activate recovery if the day has collapsed (S9-D). Returns True if active."""
    state = storage.load_recovery_state()
    if state.get('active'):
        return True

    tasks = storage.load_tasks()
    if should_trigger_recovery(tasks):
        recovery_tasks = select_recovery_tasks(tasks)
        if recovery_tasks:
            now = datetime.now()
            today = now.strftime('%Y-%m-%d')
            past_today = [t for t in tasks if _recovery_pending(t) and _task_deadline_dt(t)
                          and _task_deadline_dt(t).strftime('%Y-%m-%d') == today and _task_deadline_dt(t) < now]
            if any(getattr(t, 'deadline_type', None) == 'hard' for t in past_today):
                reason = "B"
            elif len(past_today) >= 3:
                reason = "A"
            else:
                reason = "C"
            st = storage.load_recovery_state()
            st['active'] = True
            st['triggered_at'] = now.isoformat()
            st['trigger_reason'] = reason
            st['session_tasks'] = [t.id for t in recovery_tasks]
            st['completed_in_recovery'] = []
            st['dismissed_at'] = None
            st['last_checked_date'] = today
            storage.save_recovery_state(st)
            return True

    return False

