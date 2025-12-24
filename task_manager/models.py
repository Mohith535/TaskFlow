"""
TaskFlow Models Module
---------------------
Core data models with validation and type safety.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import re


@dataclass
class Task:
    """Task model with validation and default values."""
    
    id: int
    title: str
    priority: str = "Medium"
    completed: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    completed_at: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    
    def __post_init__(self):
        """Validate task after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate task fields."""
        if not self.title or not self.title.strip():
            raise ValueError("Task title cannot be empty")
        
        if len(self.title) > 200:
            raise ValueError("Task title too long (max 200 characters)")
        
        if self.priority not in ["Low", "Medium", "High"]:
            raise ValueError(f"Invalid priority: {self.priority}")
        
        if self.completed and not self.completed_at:
            self.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    def mark_complete(self):
        """Mark task as completed."""
        self.completed = True
        self.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    def mark_pending(self):
        """Mark task as pending/undone."""
        self.completed = False
        self.completed_at = None
    
    def add_tag(self, tag: str):
        """Add a tag to the task."""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str):
        """Remove a tag from the task."""
        if tag in self.tags:
            self.tags.remove(tag)
    
    def to_dict(self):
        """Convert task to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "priority": self.priority,
            "completed": self.completed,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "tags": self.tags,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create task from dictionary."""
        return cls(**data)
    
    def __str__(self):
        """Human-readable string representation."""
        status = "✓" if self.completed else "○"
        return f"[{status}] {self.id:3d} | {self.title:30.30} | {self.priority:8}"


class TaskManager:
    """Manages collection of tasks with utility methods."""
    
    def __init__(self, tasks: list[Task] = None):
        self.tasks = tasks or []
    
    def get_next_id(self) -> int:
        """Get next available task ID."""
        if not self.tasks:
            return 1
        return max(task.id for task in self.tasks) + 1
    
    def find_task(self, task_id: int) -> Optional[Task]:
        """Find task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
    
    def add_task(self, task: Task):
        """Add a task with auto-assigned ID if needed."""
        if task.id == 0:  # New task
            task.id = self.get_next_id()
        self.tasks.append(task)
        return task.id
    
    def delete_task(self, task_id: int) -> bool:
        """Delete task by ID."""
        task = self.find_task(task_id)
        if task:
            self.tasks.remove(task)
            return True
        return False
    
    def get_stats(self) -> dict:
        """Get statistics about tasks."""
        total = len(self.tasks)
        completed = sum(1 for task in self.tasks if task.completed)
        pending = total - completed
        
        priority_stats = {"Low": 0, "Medium": 0, "High": 0}
        for task in self.tasks:
            priority_stats[task.priority] += 1
        
        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "completion_rate": (completed / total * 100) if total > 0 else 0,
            "priorities": priority_stats
        }