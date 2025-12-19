# TaskFlow

TaskFlow is a simple, terminal-based task manager built with Python.
It helps you manage tasks efficiently using clear and minimal command-line commands.

This project focuses on clarity, discipline, and extensibility, serving as a strong foundation for future productivity tools.

---

## Features

- Add new tasks
- List all tasks
- Mark tasks as completed
- Delete tasks
- View task statistics
- Built-in help command
- Persistent storage using JSON
- Clean and modular project structure

---

## Tech Stack

- Language: Python
- Interface: Command Line (CLI)
- Storage: JSON file (auto-created on first use)

---

## Project Structure

TaskFlow/
│
├── task_manager/
│   ├── __init__.py
│   ├── models.py
│   ├── storage.py
│   └── commands.py
│
├── main.py
├── README.md
└── .gitignore

---

## Getting Started

### 1. Clone the repository

git clone https://github.com/Mohith535/TaskFlow.git  
cd TaskFlow

### 2. (Optional but recommended) Create a virtual environment

python -m venv venv  
source venv/bin/activate   (On Windows: venv\Scripts\activate)

### 3. Run TaskFlow

python main.py

---

## Available Commands

python main.py add  
python main.py list  
python main.py complete <id>  
python main.py delete <id>  
python main.py stats  
python main.py help  

The tasks.json file is created automatically on first use and is intentionally ignored from version control to keep user data private.

---

## Design Philosophy

TaskFlow is intentionally kept minimal and focused.
It is designed as a core task management module, which can later integrate into higher-level productivity systems.

Future roadmap includes time-based focus tools and integration into a broader assistant system.

---

## License

This project is licensed under the MIT License.

---

## Author

K Mohith Kannan  
GitHub: https://github.com/Mohith535
