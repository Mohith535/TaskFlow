"""Kill any process on port 18082 and start a fresh server."""
import subprocess, sys, time

# Find and kill process on port 18082
result = subprocess.run(
    ['netstat', '-ano'],
    capture_output=True, text=True
)

pids_to_kill = set()
for line in result.stdout.splitlines():
    if ':18082' in line and 'LISTENING' in line:
        parts = line.split()
        if parts:
            pids_to_kill.add(parts[-1])

if not pids_to_kill:
    # Try broader search
    for line in result.stdout.splitlines():
        if ':18082' in line:
            parts = line.split()
            if parts:
                pids_to_kill.add(parts[-1])

if pids_to_kill:
    for pid in pids_to_kill:
        try:
            subprocess.run(['taskkill', '/PID', pid, '/F'], capture_output=True)
            print(f'Killed PID {pid}')
        except Exception as e:
            print(f'Could not kill {pid}: {e}')
    time.sleep(1)
else:
    print('No process found on port 18082')

# Start fresh server
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
server_path = os.path.join(os.path.dirname(__file__), 'task_manager', 'server.py')
proc = subprocess.Popen(
    [sys.executable, server_path],
    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
    if sys.platform == 'win32' else 0
)
time.sleep(2)

# Verify
import urllib.request
try:
    resp = urllib.request.urlopen('http://127.0.0.1:18082')
    body = resp.read().decode('utf-8', errors='replace')
    if 'cascadeIn' in body:
        print('SUCCESS: New Momentum Cascade server is live!')
    else:
        print('WARNING: Server alive but still serving old HTML')
        print('Body snippet:', body[:200])
except Exception as e:
    print(f'Server not responding: {e}')
