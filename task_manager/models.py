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
    deadline_raw: Optional[str] = None
    deadline_type: Optional[str] = None
    deadline_set_advance_hours: Optional[float] = None
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
    reminder_response: Optional[str] = None
    reminder_to_action_gap_minutes: Optional[float] = None

    # NEW S1 TRACKING FIELDS
    actual_start_time: Optional[str] = None
    actual_end_time: Optional[str] = None
    duration_accuracy_ratio: Optional[float] = None
    
    # NEW EVENT FIELDS
    mission_type: str = "Task"
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    
    # S3 NEW FIELDS
    pressure_level_at_completion: Optional[int] = None
    completed_under_pressure: Optional[bool] = None
    
    # S4 NEW FIELDS
    scheduled_date: Optional[str] = None
    prime_target_date: Optional[str] = None
    today_view_shown_count: int = 0
    executed_in_window: Optional[bool] = None
    window_drift_minutes: Optional[int] = None
    
    # S5 NEW FIELDS
    last_decision: Optional[str] = None
    last_decision_at: Optional[str] = None
    average_postpone_gap_hours: Optional[float] = None
    postpone_velocity: Optional[float] = None
    status: str = "todo"
    
    # ENRICHMENT NEW FIELDS
    description: Optional[str] = None
    links: List[dict] = field(default_factory=list)
    checklist: List[dict] = field(default_factory=list)
    description_updated_at: Optional[str] = None
    links_count: int = 0
    checklist_total: int = 0
    checklist_done: int = 0

    # S10 NEW FIELDS — Daily Execution Path
    planned_slot: Optional[str] = None   # "prime" | "secondary" | "low_effort" | None
    actual_slot: Optional[str] = None    # "morning" | "midday" | "evening" | None
    slot_drift: Optional[int] = None     # minutes between planned-slot target and actual completion

    # S11 NEW FIELDS — Focus Window Lock
    focus_session_count: int = 0         # how many focus sessions started on this task
    focus_total_minutes: int = 0         # total actual focus minutes accumulated
    last_focus_at: Optional[str] = None  # ISO datetime of the last focus session

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
            "actual_start_time": self.actual_start_time,
            "actual_end_time": self.actual_end_time,
            "duration_accuracy_ratio": self.duration_accuracy_ratio,
            "deadline": self.deadline,
            "deadline_raw": self.deadline_raw,
            "deadline_type": self.deadline_type,
            "deadline_set_advance_hours": self.deadline_set_advance_hours,
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
            "reminder_response": self.reminder_response,
            "reminder_to_action_gap_minutes": self.reminder_to_action_gap_minutes,
            "mission_type": self.mission_type,
            "date": self.date,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "pressure_level_at_completion": self.pressure_level_at_completion,
            "completed_under_pressure": self.completed_under_pressure,
            "scheduled_date": self.scheduled_date,
            "prime_target_date": self.prime_target_date,
            "today_view_shown_count": self.today_view_shown_count,
            "executed_in_window": self.executed_in_window,
            "window_drift_minutes": self.window_drift_minutes,
            "last_decision": self.last_decision,
            "last_decision_at": self.last_decision_at,
            "average_postpone_gap_hours": self.average_postpone_gap_hours,
            "postpone_velocity": self.postpone_velocity,
            "status": self.status,
            
            # Enrichment fields
            "description": self.description,
            "links": self.links,
            "checklist": self.checklist,
            "description_updated_at": self.description_updated_at,
            "links_count": self.links_count,
            "checklist_total": self.checklist_total,
            "checklist_done": self.checklist_done,

            # S10 fields
            "planned_slot": self.planned_slot,
            "actual_slot": self.actual_slot,
            "slot_drift": self.slot_drift,

            # S11 fields
            "focus_session_count": self.focus_session_count,
            "focus_total_minutes": self.focus_total_minutes,
            "last_focus_at": self.last_focus_at
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
        data["actual_start_time"] = data.get("actual_start_time")
        data["actual_end_time"] = data.get("actual_end_time")
        data["duration_accuracy_ratio"] = data.get("duration_accuracy_ratio")
        
        data["deadline"] = data.get("deadline")
        data["deadline_raw"] = data.get("deadline_raw")
        data["deadline_type"] = data.get("deadline_type")
        data["deadline_set_advance_hours"] = data.get("deadline_set_advance_hours")
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
        data["reminder_response"] = data.get("reminder_response")
        data["reminder_to_action_gap_minutes"] = data.get("reminder_to_action_gap_minutes")
        
        data["mission_type"] = data.get("mission_type", "Task")
        data["date"] = data.get("date")
        data["start_time"] = data.get("start_time")
        data["end_time"] = data.get("end_time")
        
        data["pressure_level_at_completion"] = data.get("pressure_level_at_completion")
        data["completed_under_pressure"] = data.get("completed_under_pressure")
        data["scheduled_date"] = data.get("scheduled_date")
        data["prime_target_date"] = data.get("prime_target_date")
        data["today_view_shown_count"] = data.get("today_view_shown_count", 0)
        data["executed_in_window"] = data.get("executed_in_window")
        data["window_drift_minutes"] = data.get("window_drift_minutes")
        data["last_decision"] = data.get("last_decision")
        data["last_decision_at"] = data.get("last_decision_at")
        data["average_postpone_gap_hours"] = data.get("average_postpone_gap_hours")
        data["postpone_velocity"] = data.get("postpone_velocity")
        data["status"] = data.get("status", "todo")
        
        # Enrichment fields
        data["description"] = data.get("description", None)
        data["links"] = data.get("links", [])
        data["checklist"] = data.get("checklist", [])
        data["description_updated_at"] = data.get("description_updated_at", None)
        data["links_count"] = data.get("links_count", 0)
        data["checklist_total"] = data.get("checklist_total", 0)
        data["checklist_done"] = data.get("checklist_done", 0)

        # S10 fields
        data["planned_slot"] = data.get("planned_slot")
        data["actual_slot"] = data.get("actual_slot")
        data["slot_drift"] = data.get("slot_drift")

        # S11 fields
        data["focus_session_count"] = data.get("focus_session_count", 0)
        data["focus_total_minutes"] = data.get("focus_total_minutes", 0)
        data["last_focus_at"] = data.get("last_focus_at")

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