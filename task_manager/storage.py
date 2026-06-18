"""
TaskFlow Storage Module
----------------------
Handles data persistence with backup and recovery.
"""

import json
import os
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from task_manager.models import Task


class TaskStorage:
    """Manages task data persistence with backup capabilities."""
    
    def __init__(self):
        # Global user-level storage directory
        self.data_dir = Path.home() / ".taskflow"   
        self.tasks_file = self.data_dir / "tasks.json"
        self.timeline_file = self.data_dir / "timeline.json"
        self.backup_dir = self.data_dir / "backups"
        self.recovery_state_file = self.data_dir / "recovery_state.json"
        self.recovery_log_file = self.data_dir / "recovery_log.json"
        self.config_file = self.data_dir / "config.json"
        # S11 — Focus Window Lock queue/state (separate from TimeTracker's focus_state.json)
        self.focus_lock_file = self.data_dir / "focus_lock.json"
        # S12 — computed daily aggregates (the behavior data store's derived layer)
        self.daily_summaries_file = self.data_dir / "daily_summaries.json"

        self._ensure_directories()

        # Migrate old local .taskflow directory if it exists
        old_dir = Path(".taskflow")
        if old_dir.exists() and not self.data_dir.exists():
            try:
                old_dir.rename(self.data_dir)
            except Exception:
                pass
    
    def _ensure_directories(self):
        """Ensure required directories exist, with private (0700) perms where supported."""
        self.data_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        # SEC-08: on POSIX, restrict the data dir so other users on a shared machine cannot read
        # tasks.json. No-op on Windows, where NTFS user-profile ACLs already restrict access.
        try:
            if os.name == 'posix':
                os.chmod(self.data_dir, 0o700)
                os.chmod(self.backup_dir, 0o700)
        except Exception:
            pass
    
    def _create_backup(self):
        """Create timestamped backup of tasks file."""
        if not self.tasks_file.exists():
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"tasks_backup_{timestamp}.json"
        shutil.copy2(self.tasks_file, backup_file)
        
        # Keep only last 10 backups
        backups = sorted(self.backup_dir.glob("tasks_backup_*.json"))
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                old_backup.unlink()
    
    def load_tasks(self) -> List[Task]:
        """
        Load tasks from JSON file with error recovery.
        
        Returns:
            List of Task objects
        """
        if not self.tasks_file.exists():
            return []
        
        try:
            with open(self.tasks_file, 'r', encoding='utf-8') as file:
                data = json.load(file)

            tasks = []
            for item in data:
                try:
                    # Handle legacy format (no tags/notes)
                    if 'tags' not in item:
                        item['tags'] = []
                    if 'notes' not in item:
                        item['notes'] = ""
                    
                    task = Task.from_dict(item)
                    tasks.append(task)
                except Exception as e:
                    print(f"Warning: Skipping invalid task data: {e}")
                    continue
            
            return tasks
            
        except json.JSONDecodeError:
            # D3-01: a corrupt tasks.json must NEVER silently become an empty board — a later
            # save would then overwrite the only copy. Quarantine the bad file, then restore the
            # newest backup that actually parses, so one bad write can't erase the user's work.
            print("Error: tasks.json is corrupted. Attempting automatic recovery from backup…")
            try:
                quarantine = self.data_dir / f"tasks_corrupt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                shutil.copy2(self.tasks_file, quarantine)
            except Exception:
                pass
            for backup in sorted(self.backup_dir.glob("tasks_backup_*.json"), reverse=True):
                try:
                    with open(backup, 'r', encoding='utf-8') as bf:
                        data = json.load(bf)
                    recovered = []
                    for item in data:
                        try:
                            recovered.append(Task.from_dict(item))
                        except Exception:
                            continue
                    shutil.copy2(backup, self.tasks_file)
                    print(f"Recovered {len(recovered)} task(s) from {backup.name}.")
                    return recovered
                except Exception:
                    continue
            print("No valid backup found. Keeping the corrupt file for inspection; starting empty.")
            return []
        except Exception as e:
            print(f"Error loading tasks: {e}")
            return []
    
    def save_tasks(self, tasks: List[Task]) -> bool:
        """
        Save tasks to JSON file with backup.
        
        Args:
            tasks: List of Task objects
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup before saving
            self._create_backup()
            
            # Convert tasks to dictionaries
            data = [task.to_dict() for task in tasks]
            
            # Save to temporary file first
            temp_file = self.tasks_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=4)
            
            # Replace original file
            temp_file.replace(self.tasks_file)
            
            return True
            
        except Exception as e:
            print(f"Error saving tasks: {e}")
            return False
    
    def export_tasks(self, export_path: str, format: str = "json") -> bool:
        """Export tasks to external file."""
        try:
            tasks = self.load_tasks()
            data = [task.to_dict() for task in tasks]
            
            export_file = Path(export_path)
            with open(export_file, 'w') as file:
                if format == "json":
                    json.dump(data, file, indent=4)
                elif format == "txt":
                    for task in tasks:
                        file.write(f"{task}\n")
            
            return True
        except Exception as e:
            print(f"Error exporting tasks: {e}")
            return False
    
    def import_tasks(self, import_path: str) -> List[Task]:
        """Import tasks from external file."""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                print(f"Error: File not found: {import_path}")
                return []
            
            with open(import_file, 'r') as file:
                data = json.load(file)
            
            tasks = []
            for item in data:
                try:
                    task = Task.from_dict(item)
                    tasks.append(task)
                except Exception as e:
                    print(f"Warning: Skipping invalid task: {e}")
                    continue
            
            return tasks
        except Exception as e:
            print(f"Error importing tasks: {e}")
            return []
    
    def get_backup_list(self) -> List[str]:
        """Get list of available backups."""
        backups = sorted(self.backup_dir.glob("tasks_backup_*.json"))
        return [b.name for b in backups]
    
    def restore_backup(self, backup_name: str) -> bool:
        """Restore from specific backup."""
        backup_file = self.backup_dir / backup_name
        if not backup_file.exists():
            return False
        
        try:
            shutil.copy2(backup_file, self.tasks_file)
            return True
        except Exception as e:
            print(f"Error restoring backup: {e}")
            return False
            
    # --- Timeline Storage Methods ---
    def load_timeline(self) -> dict:
        """Load the timeline mapping dict mapping task ID strings to date strings."""
        if not self.timeline_file.exists():
            return {}
        try:
            with open(self.timeline_file, 'r') as file:
                return json.load(file)
        except Exception as e:
            print(f"Error loading timeline mapping: {e}")
            return {}
            
    def save_timeline(self, mapping: dict) -> bool:
        """Save the timeline mapping dict to timeline.json."""
        try:
            temp_file = self.timeline_file.with_suffix('.tmp')
            with open(temp_file, 'w') as file:
                json.dump(mapping, file, indent=4)
            temp_file.replace(self.timeline_file)
            return True
        except Exception as e:
            print(f"Error saving timeline mapping: {e}")
            return False

    def load_recovery_state(self) -> dict:
        """Load the current recovery state."""
        default_state = {
            "active": False,
            "triggered_at": None,
            "trigger_reason": None,
            "session_tasks": [],
            "completed_in_recovery": [],
            "dismissed_at": None,
            "last_checked_date": None
        }
        if not self.recovery_state_file.exists():
            return default_state

        try:
            with open(self.recovery_state_file, 'r') as file:
                state = json.load(file)
            for k, v in default_state.items():
                state.setdefault(k, v)
            return state
        except Exception:
            return default_state

    def save_recovery_state(self, state: dict) -> bool:
        """Save the recovery state."""
        try:
            temp_file = self.recovery_state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as file:
                json.dump(state, file, indent=2)
            temp_file.replace(self.recovery_state_file)
            return True
        except Exception as e:
            print(f"Error saving recovery state: {e}")
            return False

    def append_recovery_log(self, entry: dict) -> bool:
        """Append an entry to the recovery log."""
        logs = []
        if self.recovery_log_file.exists():
            try:
                with open(self.recovery_log_file, 'r') as file:
                    logs = json.load(file)
            except Exception:
                logs = []
        
        logs.append(entry)
        try:
            temp_file = self.recovery_log_file.with_suffix('.tmp')
            with open(temp_file, 'w') as file:
                json.dump(logs, file, indent=2)
            temp_file.replace(self.recovery_log_file)
            return True
        except Exception as e:
            print(f"Error appending recovery log: {e}")
            return False

    def load_config(self) -> dict:
        """Load global configuration (e.g. first run flag)."""
        default_config = {
            "first_run_complete": False,
            "today_views_opened": 0,
            "last_today_view": None,
            # S10 — Daily Execution Path
            "path_generated_date": None,
            "path_tasks": [],
            "path_sections": {},
            "path_adherence_today": None,
            # S12 — Time Integrity / streak / weekly review
            "execution_streak": 0,
            "streak_last_date": None,
            "last_weekly_review": None,
            "last_summary_date": None
        }
        if not self.config_file.exists():
            return default_config
        try:
            with open(self.config_file, 'r') as file:
                config = json.load(file)
                for k, v in default_config.items():
                    if k not in config:
                        config[k] = v
                return config
        except Exception:
            return default_config

    def save_config(self, config: dict) -> bool:
        """Save global configuration."""
        try:
            temp_file = self.config_file.with_suffix('.tmp')
            with open(temp_file, 'w') as file:
                json.dump(config, file, indent=2)
            temp_file.replace(self.config_file)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def load_focus_lock(self) -> dict:
        """Load the S11 focus lock/queue state (focus_lock.json)."""
        default = {"task_id": None, "started_at": None, "queued_tasks": [], "queued_actions": []}
        if not self.focus_lock_file.exists():
            return default
        try:
            with open(self.focus_lock_file, 'r') as file:
                data = json.load(file)
            for k, v in default.items():
                data.setdefault(k, v)
            return data
        except Exception:
            return default

    def save_focus_lock(self, state: dict) -> bool:
        """Save the S11 focus lock/queue state."""
        try:
            temp_file = self.focus_lock_file.with_suffix('.tmp')
            with open(temp_file, 'w') as file:
                json.dump(state, file, indent=2)
            temp_file.replace(self.focus_lock_file)
            return True
        except Exception as e:
            print(f"Error saving focus lock: {e}")
            return False

    def load_daily_summaries(self) -> list:
        """Load the S12 computed daily summaries (list of daily aggregate dicts)."""
        if not self.daily_summaries_file.exists():
            return []
        try:
            with open(self.daily_summaries_file, 'r') as file:
                data = json.load(file)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def save_daily_summaries(self, summaries: list) -> bool:
        """Save the S12 daily summaries list."""
        try:
            temp_file = self.daily_summaries_file.with_suffix('.tmp')
            with open(temp_file, 'w') as file:
                json.dump(summaries, file, indent=2)
            temp_file.replace(self.daily_summaries_file)
            return True
        except Exception as e:
            print(f"Error saving daily summaries: {e}")
            return False


# Global storage instance
storage = TaskStorage()


# Legacy functions for backward compatibility
def load_tasks() -> List[Task]:
    return storage.load_tasks()


def save_tasks(tasks: List[Task]) -> bool:
    return storage.save_tasks(tasks)

def load_timeline() -> dict:
    return storage.load_timeline()

def save_timeline(mapping: dict) -> bool:
    return storage.save_timeline(mapping)
