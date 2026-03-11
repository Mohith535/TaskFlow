# taskflow_bg_unblocker.py
import time
import sys
import os

def main():
    if len(sys.argv) < 2:
        sys.exit(1)
        
    try:
        minutes = int(sys.argv[1])
    except ValueError:
        sys.exit(1)
    
    # Wait for the timer to expire
    time.sleep(minutes * 60)
    
    # Run the unblock command silently
    # We use os.system with python to trigger the current cli script's end_focus
    app_dir = os.path.dirname(os.path.abspath(__file__))
    cli_path = os.path.join(app_dir, "cli.py")
    
    # Run unblock script, routing output to null so it's fully silent
    # Added --force flag to bypass any "Mindful Exit" interactive prompts
    os.system(f'python "{cli_path}" focus --end --force > NUL 2>&1')

if __name__ == "__main__":
    main()
