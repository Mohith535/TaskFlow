# TaskFlow

TaskFlow is a calm, privacy-first command-line task assistant built with Python.

It helps you manage tasks with clarity and minimal cognitive load, using clean and intentional CLI commands.
Designed to feel supportive rather than demanding.


---

## Features

- Add, edit, rename, and delete tasks
- List tasks with filters (todo, done, priority)
- Mark tasks as completed or undo completion
- Task priorities (low / medium / high)
- Focus sessions with time tracking
- Task scheduling (today, tomorrow, date-based)
- Notes and tags for tasks
- Human-readable summaries and statistics
- Built-in help with calm, non-intrusive messaging
- Safe local persistence with automatic backups


---

## Tech Stack

- Language: Python
- Interface: Command Line (CLI)
- Storage: Local JSON (stored safely in user home directory)

---

## Project Structure

TaskFlow/
│
├── taskflow/
│   ├── __init__.py
│   └── cli.py          # CLI entrypoint
│
├── task_manager/
│   ├── __init__.py
│   ├── models.py
│   ├── storage.py
│   └── commands.py
│
├── setup.py
├── README.md
└── .gitignore

---

## Getting Started

## Installation

Install TaskFlow directly from GitHub:

pip install --upgrade git+https://github.com/Mohith535/TaskFlow.git


---


## Usage

Once installed, TaskFlow is available as a global command:

taskflow add
taskflow list
taskflow list --todo
taskflow complete <id>
taskflow focus --id <id>
taskflow stats
taskflow help 

The tasks.json file is created automatically on first use and is intentionally ignored from version control to keep user data private.

---

## Data & Privacy

TaskFlow stores all user data locally in:

~/.taskflow

- No cloud sync
- No telemetry
- No tracking
- No background services

All data stays on your machine.

---

## Design Philosophy

TaskFlow is intentionally calm, minimal, and focused.
It is designed as a core task management module, which can later integrate into higher-level productivity systems.

Future roadmap includes time-based focus tools and integration into a broader assistant system.

---

## License

This project is licensed under the MIT License.

---

## Author

K Mohith Kannan  
GitHub: https://github.com/Mohith535

