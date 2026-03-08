# 🌊 TaskFlow v3.0.0

**TaskFlow** is a calm, privacy-first command-line task assistant built with Python. 

It helps you manage tasks with clarity and minimal cognitive load, using clean and intentional CLI commands. Designed to feel supportive rather than demanding, TaskFlow now includes a robust **Distraction Blocking Engine** to help you maintain deep focus.

---

## ✨ Features

### 📋 Core Task Management
- **Add, edit, rename, and delete tasks** fluidly from your terminal.
- **List tasks with filters** (`--todo`, `--done`, `--priority`, `--tag`).
- **Prioritize** your work (Low / Medium / High).
- **Schedule tasks** using natural language (e.g., `today`, `tomorrow`, `YYYY-MM-DD`).
- **Add notes & tags** for contextual organization.
- **Stats & Summaries:** Human-readable overviews of your productivity.

### 🎯 v3.0.0 Focus Engine & Distraction Blocking
- **Focus Sessions:** Start timed work sessions tied directly to specific tasks.
- **Gentle Mode:** Reminders via console notifications when you're trying to avoid distracting apps and sites.
- **Strict Mode (Windows Admin):** Deep system-level intervention that modifies the Windows `hosts` file to forcefully block websites and uses `taskkill` to close distracting applications.
- **Aggressive Connection Termination:** Automatically force-closes browsers at the start of Strict Mode to sever hidden persistent DNS connections (QUIC/WebSockets).
- **Background Auto-Unblocker:** A lightweight, detached background worker silently tracks your session and restores your `hosts` file securely when your timer expires, even if you close the terminal.
- **Self-Healing:** Automatically detects and resolves orphaned system blocks on startup in case of ungraceful exits or PC crashes.

---

## 🛠️ Tech Stack & Architecture

- **Language:** Python 3.x
- **Interface:** Command Line (CLI) via `argparse`
- **Storage:** Local JSON (stored safely in `~/.taskflow/tasks.json`)
- **Logging:** Background actions tracked in `~/.taskflow/taskflow.log`

### Project Structure

```text
TaskFlow/
├── taskflow/
│   ├── __init__.py
│   ├── cli.py                    # Main CLI router & entrypoint
│   └── taskflow_bg_unblocker.py  # Detached async focus unblocker
│
├── task_manager/
│   ├── __init__.py
│   ├── models.py                 # Data structures
│   ├── storage.py                # Local JSON persistence
│   ├── system_detector.py        # OS environment routing
│   ├── commands.py               # Core logic (FocusManager, TimeTracker)
│   └── blockers/
│       ├── base.py               # Abstract blocking logic & logging
│       ├── gentle.py             # Reminder-based cross-platform blocker
│       └── windows.py            # Aggressive system-level hosts/process blocker
│
├── setup.py
├── README.md
└── .gitignore
```

---

## 🚀 Getting Started

### Installation

Install TaskFlow directly from GitHub:

```bash
pip install --upgrade git+https://github.com/Mohith535/TaskFlow.git
```

### Basic Usage

Once installed, `taskflow` is available globally in your terminal:

```bash
# Task Management
taskflow add
taskflow list --todo --priority high
taskflow complete 1

# Focus & Blocking (Strict Mode requires running terminal as Administrator)
taskflow focus --id 1 --minutes 25 --block-sites youtube.com twitter.com --mode strict

# Maintenance
taskflow stats
taskflow summary
taskflow help
```

---

## 🔒 Data & Privacy

TaskFlow is designed with extreme privacy in mind. It stores all user data locally in:

`~/.taskflow`

- ❌ **No cloud sync**
- ❌ **No telemetry**
- ❌ **No tracking**
- ❌ **No background services** *(Except the temporary auto-unblock worker during active focus sessions)*

**All data stays on your machine.**

---

## 🧘‍♂️ Design Philosophy

TaskFlow is intentionally calm, minimal, and focused. It is designed as a core task management module, which can later integrate into higher-level productivity systems.

The v3.0.0 updates bring a robust, fault-tolerant focus engine to the completely offline, terminal-first environment. 

---

## 📄 License
This project is licensed under the **MIT License**.

## 👨‍💻 Author
**K Mohith Kannan**  
GitHub: [@Mohith535](https://github.com/Mohith535)

