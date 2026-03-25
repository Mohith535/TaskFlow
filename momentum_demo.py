# TaskFlow | Momentum Cascade Demo
# 
# Instructions:
# 1. Ensure 'rich' and 'textual' are installed:
#    pip install rich textual
# 
# 2. Run this script to initiate the Momentum Cascade:
#    python momentum_demo.py
# 
# 3. Features to observe:
#    [x] Gentle Cascade: Tasks flow down domino-style
#    [x] Magnetic Selection: Lift effects on selection
#    [x] Success Ripple: Green wave on task completion (Enter)
#    [x] Completion Horizon: Progress bar advancement

import sys
import os
import time

# Ensure imports work from current directory
sys.path.append(os.getcwd())

try:
    from taskflow.ui.cascade import run_momentum
except ImportError:
    print("Error: 'rich' and 'textual' are not installed.")
    print("Please run: pip install rich textual")
    sys.exit(1)

if __name__ == "__main__":
    print("\033[2J") # Clear screen
    print("\n  TaskFlow | Momentum Cascade Protocol")
    print("  -----------------------------------")
    print("  Preparing mission localizer...")
    time.sleep(2)
    
    run_momentum()
