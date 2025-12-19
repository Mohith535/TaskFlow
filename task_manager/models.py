from dataclasses import dataclass

@dataclass
class Task:
    def __init__(
        self,
        id,
        title,
        priority,
        completed=False,
        created_at=None,
        completed_at=None
    ):
        self.id = id
        self.title = title
        self.priority = priority
        self.completed = completed
        self.created_at = created_at
        self.completed_at = completed_at

