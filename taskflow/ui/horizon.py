# Momentum Cascade Completion Horizon
# Always-visible progress bar for the terminal footer

from rich.progress import Progress, BarColumn, TextColumn
from .palette import COMPLETED

def get_horizon(total, done):
    """Return a rich renderable for the completion horizon."""
    percent = (done / total) * 100 if total > 0 else 0
    
    p = Progress(
        TextColumn("[bold white]Momentum[/bold white]"),
        BarColumn(bar_width=None, complete_style=COMPLETED, finished_style=f"bold {COMPLETED}"),
        TextColumn(f"[bold white]{done}/{total}[/bold white] [dim]{percent:>3.0f}%[/dim]"),
        expand=True
    )
    p.add_task("Horizon", total=total, completed=done)
    return p
