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
        self.backup_dir = self.data_dir / "backups"
        
        self._ensure_directories()

        # Migrate old local .taskflow directory if it exists
        old_dir = Path(".taskflow")
        if old_dir.exists() and not self.data_dir.exists():
            try:
                old_dir.rename(self.data_dir)
            except Exception:
                pass
    
    def _ensure_directories(self):
        """Ensure required directories exist."""
        self.data_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
    
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
            with open(self.tasks_file, 'r') as file:
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
            print("Error: Corrupted tasks file. Attempting recovery...")
            self._create_backup()
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
            with open(temp_file, 'w') as file:
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


# Global storage instance
storage = TaskStorage()


# Legacy functions for backward compatibility
def load_tasks() -> List[Task]:
    return storage.load_tasks()


def save_tasks(tasks: List[Task]) -> bool:
    return storage.save_tasks(tasks)
