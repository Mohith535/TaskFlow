import sys
import os

# Add parent directory to path to ensure imports work if run directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    from taskflow.cli import main as cli_main
    cli_main()

if __name__ == "__main__":
    main()
