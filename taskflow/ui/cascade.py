# Momentum Cascade Animation Engine
# Core TUI logic for "Effortless Mastery" tasks

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, ListView, ListItem, Label, Static
from textual.containers import Container, Vertical
from textual.binding import Binding
from textual import on
from textual.reactive import reactive
import asyncio

from .palette import *
from .states import get_victory_state
from .horizon import get_horizon
from task_manager.storage import storage
from rich.text import Text

class MissionItem(ListItem):
    """A magnetic, premium mission row with lift + glow."""
    
    glow_intensity = reactive(0.0)

    def __init__(self, task):
        super().__init__()
        self.task = task
        self.is_completed = task.completed
        self.styles.height = 3
        self.styles.margin = (0, 0, 1, 0)
        self.styles.padding = (0, 2)
        self.styles.background = BG_SUBTLE
        self.styles.border = ("thin", "gray", 0.1)
        self.styles.transition = "offset 200ms ease-in-out, background 300ms, border 300ms"

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

    def watch_glow_intensity(self, intensity: float) -> None:
        """Update border color based on progressive glow."""
        if intensity > 0:
            self.styles.border = ("thick", f"rgba(74, 222, 128, {intensity})")
        else:
            self.styles.border = ("thin", "gray", 0.1)

    def on_enter(self) -> None:
        # PREMIUM HOVER (MAGNETIC LIFT)
        self.styles.animate("offset", value=(0, -1), duration=0.2)
        self.styles.animate("glow_intensity", value=1.0, duration=0.3)
        self.styles.background = GLOW_ALPHA
        self.styles.text_style = "bold"

    def on_leave(self) -> None:
        if not self.has_focus:
            self.styles.animate("offset", value=(0, 0), duration=0.2)
            self.styles.animate("glow_intensity", value=0.0, duration=0.3)
            self.styles.background = BG_SUBTLE
            self.styles.text_style = "none"

    def on_focus(self):
        # MAGNETIC SELECTION (LIFT EFFECT)
        self.styles.animate("offset", value=(0, -1), duration=0.2)
        self.styles.animate("glow_intensity", value=1.0, duration=0.2)
        self.styles.background = "linear-gradient(rgba(74,222,128,0.2), rgba(74,222,128,0.1))"
        self.styles.margin = (0, 0, 1, 2)

    def on_blur(self):
        self.styles.animate("offset", value=(0, 0), duration=0.2)
        self.styles.animate("glow_intensity", value=0.0, duration=0.2)
        self.styles.background = BG_SUBTLE
        self.styles.margin = (0, 0, 1, 0)
        self.styles.text_style = "none"

    def trigger_success_ripple(self):
        # SUCCESS RIPPLE (GREEN WAVE)
        self.styles.animate("background", value=COMPLETED, duration=0.2)
        def reset_bg(): self.styles.animate("background", value=BG_SUBTLE, duration=0.4)
        asyncio.get_event_loop().call_later(0.3, reset_bg)

class MissionList(ListView):
    """A premium mission list with coordinated highlights."""
    pass

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
        border: none;
    }
    MissionItem {
        background: #0f172a;
        margin-bottom: 1;
        border: thin gray 0.1;
        border-radius: 4;
    }
    MissionItem:hover {
        background: rgba(74, 222, 128, 0.15);
        border: heavy #4ade80;
    }
    MissionItem:focus {
        background: #1e293b;
        border: heavy #4ade80;
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
            MissionList(id="task-list"),
            Static(id="victory-pane"),
            Static(id="horizon-pane"),
            id="main-container"
        )
        yield Footer()

    async def on_mount(self):
        self.tasks = storage.load_tasks()
        await self.cascade_render()

    async def cascade_render(self) -> None:
        # GENTLE CASCADE (DOMINO EFFECT)
        task_list = self.query_one("#task-list", MissionList)
        task_list.clear()
        
        for task in self.tasks:
            if not task.completed:  # Focus on pending tasks for momentum
                await asyncio.sleep(0.1)
                task_list.append(MissionItem(task))
        
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

    async def action_complete_selected(self) -> None:
        task_list = self.query_one("#task-list", MissionList)
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
