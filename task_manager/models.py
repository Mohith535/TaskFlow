from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import re


@dataclass
class Task:
    """Task model with validation and default values."""
    
    id: int
    title: str
    priority: str = "Medium"
    completed: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M'))
    completed_at: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    focus_minutes_spent: int = 0  # NEW: Track focus time
    duration: Optional[str] = None
    deadline: Optional[str] = None
    deadline_type: Optional[str] = None
    postpone_count: int = 0
    last_missed_prompt: Optional[str] = None
    executed_late: Optional[bool] = None
    dropped_at: Optional[str] = None
    drop_reason: Optional[str] = None
    offloaded_at: Optional[str] = None
    offload_note: Optional[str] = None
    postpone_history: List[str] = field(default_factory=list)
    reminder_time: Optional[str] = None
    reminder_time_2: Optional[str] = None
    reminder_fired: bool = False
    reminder_fired_2: bool = False
    reminder_dismissed: bool = False
    
    # NEW EVENT FIELDS
    mission_type: str = "Task"
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    
    def __post_init__(self):
        """Validate task after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate task fields."""
        if not self.title or not self.title.strip():
            raise ValueError("Task title cannot be empty")
        
        if len(self.title) > 200:
            raise ValueError("Task title too long (max 200 characters)")
        
        if self.priority not in ["Low", "Medium", "High", "Critical", "Strategic", "Noise", "Purge"]:
            raise ValueError(f"Invalid priority: {self.priority}")
        
        if self.completed and not self.completed_at:
            self.completed_at = datetime.now().strftime('%Y-%m-%d %H:%M')
            
        if self.duration:
            self.duration = self.duration.lower()
            
    def mark_complete(self):
        """Mark task as completed."""
        self.completed = True
        self.completed_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    
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
    
    def add_focus_minutes(self, minutes: int):
        """Add focus minutes to task."""
        self.focus_minutes_spent += minutes
    
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
            "notes": self.notes,
            "focus_minutes_spent": self.focus_minutes_spent,
            "duration": self.duration,
            "deadline": self.deadline,
            "deadline_type": self.deadline_type,
            "postpone_count": self.postpone_count,
            "last_missed_prompt": self.last_missed_prompt,
            "executed_late": self.executed_late,
            "dropped_at": self.dropped_at,
            "drop_reason": self.drop_reason,
            "offloaded_at": self.offloaded_at,
            "offload_note": self.offload_note,
            "postpone_history": self.postpone_history,
            "reminder_time": self.reminder_time,
            "reminder_time_2": self.reminder_time_2,
            "reminder_fired": self.reminder_fired,
            "reminder_fired_2": self.reminder_fired_2,
            "reminder_dismissed": self.reminder_dismissed,
            "mission_type": self.mission_type,
            "date": self.date,
            "start_time": self.start_time,
            "end_time": self.end_time
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create task from dictionary."""
        # Handle legacy tasks without new fields
        if "tags" not in data:
            data["tags"] = []
        if "notes" not in data:
            data["notes"] = ""
        if "focus_minutes_spent" not in data:
            data["focus_minutes_spent"] = 0
            
        # Get optional new fields with safe defaults
        data["duration"] = data.get("duration")
        data["deadline"] = data.get("deadline")
        data["deadline_type"] = data.get("deadline_type")
        data["postpone_count"] = data.get("postpone_count", 0)
        data["last_missed_prompt"] = data.get("last_missed_prompt")
        data["executed_late"] = data.get("executed_late")
        data["dropped_at"] = data.get("dropped_at")
        data["drop_reason"] = data.get("drop_reason")
        data["offloaded_at"] = data.get("offloaded_at")
        data["offload_note"] = data.get("offload_note")
        data["postpone_history"] = data.get("postpone_history", [])
        data["reminder_time"] = data.get("reminder_time")
        data["reminder_time_2"] = data.get("reminder_time_2")
        data["reminder_fired"] = data.get("reminder_fired", False)
        data["reminder_fired_2"] = data.get("reminder_fired_2", False)
        data["reminder_dismissed"] = data.get("reminder_dismissed", False)
        
        data["mission_type"] = data.get("mission_type", "Task")
        data["date"] = data.get("date")
        data["start_time"] = data.get("start_time")
        data["end_time"] = data.get("end_time")
        
        return cls(**data)
    
    def __str__(self):
        """Human-readable string representation."""
        status = "✓" if self.completed else "○"
        return f"[{status}] {self.id:3d} | {self.title[:30]:30.30} | {self.priority:8}"


class TaskManager:
    """Manages collection of tasks with utility methods."""
    
    def __init__(self, tasks: List[Task] = None):
        self.tasks = tasks or []
        self._task_by_id = {task.id: task for task in self.tasks}  # Index for O(1) lookup
    
    def get_next_id(self) -> int:
        """Get next available task ID."""
        if not self.tasks:
            return 1
        return max(task.id for task in self.tasks) + 1
    
    def find_task(self, task_id: int) -> Optional[Task]:
        """Find task by ID in O(1) time."""
        return self._task_by_id.get(task_id)
    
    def add_task(self, task: Task):
        """Add a task with auto-assigned ID if needed."""
        if task.id == 0:  # New task
            task.id = self.get_next_id()
        self.tasks.append(task)
        self._task_by_id[task.id] = task  # Update index
        return task.id
    
    def delete_task(self, task_id: int) -> bool:
        """Delete task by ID."""
        task = self.find_task(task_id)
        if task:
            self.tasks.remove(task)
            del self._task_by_id[task_id]
            return True
        return False
    
    def get_stats(self) -> dict:
        """Get statistics about tasks."""
        total = len(self.tasks)
        completed = sum(1 for task in self.tasks if task.completed)
        pending = total - completed
        
        priority_stats = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0, "Strategic": 0, "Noise": 0, "Purge": 0}
        total_focus_minutes = 0
        
        for task in self.tasks:
            p = task.priority
            if p not in priority_stats:
                priority_stats[p] = 0
            priority_stats[p] += 1
            total_focus_minutes += task.focus_minutes_spent
        
        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "completion_rate": (completed / total * 100) if total > 0 else 0,
            "priorities": priority_stats,
            "total_focus_minutes": total_focus_minutes
        }