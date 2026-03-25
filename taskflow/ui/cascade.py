# Momentum Cascade Animation Engine
# Core TUI logic for "Effortless Mastery" tasks

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, ListView, ListItem, Label, Static
from textual.containers import Container, Vertical
from textual.binding import Binding
from textual import on
import asyncio

from .palette import *
from .states import get_victory_state
from .horizon import get_horizon
from task_manager.storage import storage
from rich.text import Text

class TaskItem(ListItem):
    """A magnetic, responsive task row."""
    def __init__(self, task):
        super().__init__()
        self.task = task
        self.is_completed = task.completed
        self.styles.height = 3
        self.styles.margin = (0, 0, 1, 0)
        self.styles.padding = (0, 2)
        self.styles.background = BG_SUBTLE
        self.styles.border = ("thin", "gray", 0.1)

    def compose(self) -> ComposeResult:
        marker = "■" if self.is_completed else "□"
        color = COMPLETED if self.is_completed else self.get_priority_color()
        
        with Vertical():
            yield Label(f"{marker} [bold {color}]{self.task.title}[/bold {color}]", id="title")
            yield Label(f"[dim]{self.task.priority.upper()}[/dim]  [dim italic]#{' #'.join(self.task.tags)}[/dim]", id="meta")

    def get_priority_color(self):
        p = self.task.priority.lower()
        if p == "high": return HIGH
        if p == "low": return LOW
        return MEDIUM

    def on_focus(self):
        # MAGNETIC SELECTION (LIFT EFFECT)
        self.styles.border = ("thick", COMPLETED)
        self.styles.animate("margin", value=(0, 0, 1, 2), duration=0.2)
        self.styles.background = "#1e293b"

    def on_blur(self):
        self.styles.border = ("thin", "gray", 0.1)
        self.styles.animate("margin", value=(0, 0, 1, 0), duration=0.2)
        self.styles.background = BG_SUBTLE

    def trigger_success_ripple(self):
        # SUCCESS RIPPLE (GREEN WAVE)
        self.styles.animate("background", value=COMPLETED, duration=0.2)
        def reset_bg(): self.styles.animate("background", value=BG_SUBTLE, duration=0.4)
        asyncio.get_event_loop().call_later(0.3, reset_bg)

class MomentumApp(App):
    """The Momentum Cascade TUI Application."""
    CSS = """
    Screen {
        background: #020617;
    }
    #task-list {
        background: transparent;
        padding: 1 4;
        height: 1fr;
    }
    #horizon-pane {
        height: auto;
        padding: 1 4;
        border-top: solid #1e293b;
    }
    #victory-pane {
        height: 3;
        content-align: center middle;
        color: #94a3b8;
        text-style: italic;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("enter", "complete_selected", "Complete (Enter)"),
        Binding("up", "cursor_up", "Select"),
        Binding("down", "cursor_down", "Select"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Vertical(
            ListView(id="task-list"),
            Static(id="victory-pane"),
            Static(id="horizon-pane"),
            id="main-container"
        )
        yield Footer()

    async def on_mount(self):
        self.tasks = storage.load_tasks()
        await self.cascade_render()

    async def cascade_render(self):
        # GENTLE CASCADE (DOMINO EFFECT)
        task_list = self.query_one("#task-list", ListView)
        task_list.clear()
        
        for task in self.tasks:
            if not task.completed:  # Focus on pending tasks for momentum
                await asyncio.sleep(0.1)
                task_list.append(TaskItem(task))
        
        self.update_hud()

    def update_hud(self):
        total = len(self.tasks)
        done = len([t for t in self.tasks if t.completed])
        
        # COMPLETION HORIZON
        horizon = self.query_one("#horizon-pane", Static)
        horizon.update(get_horizon(total, done))
        
        # VICTORY STATES
        victory = self.query_one("#victory-pane", Static)
        victory.update(get_victory_state(total, done))

    async def action_complete_selected(self):
        task_list = self.query_one("#task-list", ListView)
        if task_list.index is not None:
            item = task_list.children[task_list.index]
            
            # SUCCESS RIPPLE
            item.trigger_success_ripple()
            
            # Update data
            item.task.completed = True
            storage.save_tasks(self.tasks)
            
            # Advance HUD
            self.update_hud()
            
            # Remove from list after animation
            def remove_item(): 
                task_list.children[task_list.index].remove()
            asyncio.get_event_loop().call_later(0.5, remove_item)

def run_momentum():
    app = MomentumApp()
    app.run()
