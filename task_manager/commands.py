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
from .system_detector import SystemDetector
from .blockers import GentleBlocker  # For fallback
from .blockers.blocklist import blocklist_manager


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
                    if stats.get('last_cycle_date') == today:
                        return stats.get('cycles_today', 0)
        except:
            pass
        return 0
        
    def increment_cycle(self):
        try:
            from task_manager.storage import storage
            stats_file = storage.data_dir / "user_stats.json"
            stats = {'cycles_today': 0, 'last_cycle_date': '', 'streak_days': 0}
            if stats_file.exists():
                try:
                    with open(stats_file, 'r') as f:
                        stats.update(json.load(f))
                except: pass
                
            today = datetime.now().strftime('%Y-%m-%d')
            if stats.get('last_cycle_date') == today:
                stats['cycles_today'] += 1
            else:
                last_date_str = stats.get('last_cycle_date', '')
                if last_date_str:
                    try:
                        last_date = datetime.strptime(last_date_str, '%Y-%m-%d')
                        # Check streak
                        if (datetime.now() - last_date).days == 1:
                            stats['streak_days'] += 1
                        else:
                            stats['streak_days'] = 1
                    except:
                        stats['streak_days'] = 1
                else:
                    stats['streak_days'] = 1
                
                stats['cycles_today'] = 1
                stats['last_cycle_date'] = today
                
            with open(stats_file, 'w') as f:
                json.dump(stats, f)
        except:
            pass
    
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

def kill_web_ui():
    """Find and terminate any existing Web UI server processes on port 18083."""
    import subprocess
    import sys
    import os
    import signal
    import re

    port = 18083
    print(f"📡 Scanning for Mission Control processes on port {port}...")
    
    try:
        if sys.platform == "win32":
            # Windows: Find PID using netstat
            cmd = f'netstat -ano | findstr :{port}'
            output = subprocess.check_output(cmd, shell=True).decode()
            pids = set()
            for line in output.strip().split('\n'):
                if 'LISTENING' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pids.add(parts[4])
            
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
                pid = subprocess.check_output(cmd, shell=True).decode().strip()
                if pid:
                    print(f"🛑 Terminating PID {pid}...")
                    os.kill(int(pid), signal.SIGKILL)
                else:
                    print("✅ No active server processes found.")
                    return True
            except subprocess.CalledProcessError:
                print("✅ No active server processes found.")
                return True

        print("✨ Mission Control cleared.")
        return True
    except Exception as e:
        print(f"⚠️  Error during cleanup: {e}")
        return False


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


def list_tasks(filter_status: Optional[str] = None, 
               filter_priority: Optional[str] = None,
               filter_tag: Optional[str] = None,
               show_all: bool = False,
               sort_by: Optional[str] = None) -> None:
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
            key=lambda t: t.due_date or "9999-12-31"
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

    # Gentle UX hint for sorting (only when useful)
    if not sort_by and len(filtered_tasks) > 5:
        Messenger.note(
            "Tip: Use --sort priority or --sort due to organize tasks."
        )



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