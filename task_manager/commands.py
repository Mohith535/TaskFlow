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

def format_time_remaining(td: timedelta) -> str:
    secs = int(td.total_seconds())
    if secs >= 0:
        if secs > 3600:
            h = secs // 3600
            m = (secs % 3600) // 60
            return f"{h}h {m}m remaining" if m > 0 else f"{h}h remaining"
        elif secs >= 60:
            return f"{secs // 60}m remaining"
        else:
            return f"{secs}s remaining"
    else:
        secs = abs(secs)
        if secs > 3600:
            h = secs // 3600
            m = (secs % 3600) // 60
            return f"OVERDUE {h}h {m}m" if m > 0 else f"OVERDUE {h}h"
        else:
            return f"OVERDUE {secs // 60}m"

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
            # Overdue
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

def postpone_flow(task: Task, tasks: List[Task], original_deadline: datetime, today_str: str) -> bool:
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
        return postpone_flow(task, tasks, original_deadline, today_str)



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
    
    if duration:
        task.duration = duration.lower()
        
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


def list_tasks(filter_status: Optional[str] = None,
               filter_priority: Optional[str] = None,
               filter_tag: Optional[str] = None,
               show_all: bool = False,
               sort_by: Optional[str] = None,
               show_detail: bool = False) -> None:
    """List tasks with advanced filtering and optional enrichment details."""
    tasks = storage.load_tasks()
    print_list_missed_banner(tasks)  # PASSIVE notice only — never prompts (see: taskflow missed)

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
    
    def get_indicator_str(t) -> str:
        import sys
        supports_emoji = False
        try:
            encoding = sys.stdout.encoding or 'ascii'
            if 'utf' in encoding.lower() or 'cp65001' in encoding.lower():
                supports_emoji = True
        except Exception:
            pass
            
        parts = []
        if getattr(t, 'description', None):
            parts.append("📝" if supports_emoji else "[note]")
        if getattr(t, 'links', None):
            count = len(t.links)
            parts.append(f"🔗 ×{count}" if supports_emoji else f"[{count} links]")
        if getattr(t, 'checklist', None):
            done = sum(1 for x in t.checklist if x.get("done"))
            total = len(t.checklist)
            parts.append(f"☑ {done}/{total}" if supports_emoji else f"[{done}/{total}]")
            
        if not parts:
            return ""
        return "     " + " · ".join(parts)

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
                    if dt.tzinfo is not None:
                        dt = dt.replace(tzinfo=None)
                    td = dt - datetime.now()
                    rem_str = format_time_remaining(td)
                    
                    if pressure == 3:
                        title_color = Fore.RED + Style.BRIGHT
                        if td.total_seconds() < 0:
                            pressure_suffix = f" · {Fore.RED + Style.BRIGHT}{rem_str}{Style.RESET_ALL}"
                        else:
                            pressure_suffix = f" · {Fore.RED + Style.BRIGHT}{rem_str} ⚠{Style.RESET_ALL}"
                        if getattr(task, 'deadline_type', None) == "hard":
                            hard_pressure_line = f"\n     → {Fore.RED}Hard deadline. Execute or reschedule now.{Style.RESET_ALL}"
                    elif pressure == 2:
                        title_color = Fore.YELLOW + Style.BRIGHT
                        pressure_suffix = f" · {Fore.YELLOW + Style.BRIGHT}{rem_str}{Style.RESET_ALL}"
                        if getattr(task, 'deadline_type', None) == "hard":
                            hard_pressure_line = f"\n     → {Fore.RED}Hard deadline. Execute or reschedule now.{Style.RESET_ALL}"
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
        
        # Build the final string
        id_str = f"{Fore.GREEN}#{task.id}{Style.RESET_ALL}"
        
        # S1-D: Duration appears between title and priority.
        duration_part = f"  [{task.duration}] " if task.duration else ""
        
        deadline_str = format_deadline_display(task)
        if deadline_str:
            deadline_str = f" · {deadline_str}"
            
        base = f"{id_str} · {title_color}{task.title}{Style.RESET_ALL}{duration_part}{priority_str}{tags_str}{pressure_suffix}{postpone_suffix}\n     Deadline: {deadline_str.strip(' ·')}"
        if not getattr(task, 'deadline', None):
            base = f"{id_str} · {title_color}{task.title}{Style.RESET_ALL}{duration_part}{priority_str}{tags_str}{pressure_suffix}{postpone_suffix}"
        
        base += hard_pressure_line
        
        detail_lines = []
        if show_detail:
            if getattr(task, 'description', None):
                preview = task.description.replace('\n', ' ')
                if len(preview) > 80:
                    preview = preview[:77] + "..."
                detail_lines.append(f"     Notes: {preview}")
            if getattr(task, 'links', None):
                for l in task.links:
                    title_part = f" (\"{l.get('title')}\")" if l.get('title') else ""
                    detail_lines.append(f"     Link: [{l.get('id')}] {l.get('type')} → {l.get('url')}{title_part}")
            if getattr(task, 'checklist', None):
                for idx, item in enumerate(task.checklist):
                    chk = "✓" if item.get("done") else "·"
                    detail_lines.append(f"     Subtask {idx+1}: [{chk}] {item.get('text')}")
        
        if task.completed:
            # Overwrite base format for completed tasks to match old style but dim
            base = f"{id_str} · {title_color}{task.title}{Style.RESET_ALL}{duration_part}{priority_str}{tags_str}{deadline_str}"
            print(f"{Fore.GREEN}✓{Style.RESET_ALL} {Style.DIM}{base}{Style.RESET_ALL}")
            ind = get_indicator_str(task)
            if ind:
                print(Style.DIM + ind + Style.RESET_ALL)
            if show_detail:
                for dl in detail_lines:
                    print(Style.DIM + dl + Style.RESET_ALL)
        elif task.dropped_at or task.offloaded_at:
            base = f"{id_str} · {title_color}{task.title}{Style.RESET_ALL}{duration_part}{priority_str}{tags_str}{deadline_str}"
            print(f"{Fore.RED}x{Style.RESET_ALL} {Style.DIM}{base}{Style.RESET_ALL}")
            ind = get_indicator_str(task)
            if ind:
                print(Style.DIM + ind + Style.RESET_ALL)
            if show_detail:
                for dl in detail_lines:
                    print(Style.DIM + dl + Style.RESET_ALL)
        else:
            print(f"{Fore.YELLOW}○{Style.RESET_ALL} {base}")
            ind = get_indicator_str(task)
            if ind:
                print(ind)
            if show_detail:
                for dl in detail_lines:
                    print(dl)
            
        shown += 1
    
    print(f"\n{Style.DIM}Total: {len(filtered_tasks)} task(s){Style.RESET_ALL}")

    # Gentle UX hint for sorting (only when useful)
    if not sort_by and len(filtered_tasks) > 5:
        Messenger.note(
            "Tip: Use --sort priority or --sort due to organize tasks."
        )

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
            rem_str = format_time_remaining(td)
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
            rem_str = format_time_remaining(dt - now)
            suffix += f"  ← {rem_str}"
        else:
            rem_str = format_time_remaining(dt - now)
            suffix += f"  ← {rem_str}"

        if getattr(task, 'deadline_type', None) == "hard":
            suffix = f"  {Fore.RED}[HARD]{Style.RESET_ALL}" + suffix
            
        # S4-E Brackets around time stamp
        print(row_color + f"{prefix}{time_str}  {task.title:<26}{Style.RESET_ALL}{dur_display}{suffix}")
        
        if is_now or is_next or is_window:
            if is_next:
                duration_part = f"Est. duration: {task.duration}" if task.duration else "No estimated duration"
                ends_part = ""
                if task.duration:
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
                print(row_color + f"           {duration_part}{ends_part}" + Style.RESET_ALL)
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
                    td = datetime.fromisoformat(task.deadline) - now
                    if td.tzinfo is not None:
                        td = td.replace(tzinfo=None)
                    rem_str = format_time_remaining(td)
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
        uncompleted_timed = [t for t in timed_tasks]
        if not uncompleted_timed and untimed_tasks:
            pass 
        elif not uncompleted_timed:
            pass
        else:
            print("All scheduled windows have passed.")
    print()
    print_today_missed_notice(tasks)  # PASSIVE bottom notice — never prompts (see: taskflow missed)


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
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
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
                        if dt.tzinfo is not None:
                            dt = dt.replace(tzinfo=None)
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

