# TaskFlow Momentum Entry Point
# Bridges the CLI with the high-fidelity TUI cascade

import sys
import os

# Add parent directory to path to ensure imports work if run directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from taskflow.ui.cascade import run_momentum

def main():
    """
    Entry point for the Momentum Cascade experience.
    Commands:
        taskflow list -> Triggers the TUI cascade
        taskflow <cmd> -> Falls back to standard CLI
    """
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        try:
            run_momentum()
        except ImportError:
            print("Momentum UI requires 'rich' and 'textual'.")
            print("Please run: pip install rich textual")
            from taskflow.cli import main as cli_main
            cli_main()
    else:
        from taskflow.cli import main as cli_main
        cli_main()

if __name__ == "__main__":
    main()
