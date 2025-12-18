from dataclasses import dataclass

@dataclass
class Task:
    id: int
    title: str
    priority: str
    completed: bool = False
