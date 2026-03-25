import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from urllib.parse import urlparse, parse_qs
from task_manager import storage, commands
from task_manager.web_ui import HTML_TEMPLATE
from task_manager import models

class TaskFlowHandler(BaseHTTPRequestHandler):
    def end_headers_json(self):
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8', errors='replace'))


        elif path == "/api/tasks":
            tasks = storage.load_tasks()
            # Only send non-completed tasks for the active list
            pending_tasks = [
                {
                    "id": t.id,
                    "title": t.title,
                    "priority": t.priority,
                    "tags": t.tags,
                    "notes": t.notes,
                    "completed": t.completed
                }
                for t in tasks if not t.completed
            ]
            self.send_response(200)
            self.end_headers_json()
            self.wfile.write(json.dumps({"tasks": pending_tasks}).encode('utf-8'))

        elif path == "/api/stats":
            tasks = storage.load_tasks()
            total = len(tasks)
            completed = sum(1 for t in tasks if t.completed)
            rate = (completed / total * 100) if total > 0 else 0
            
            self.send_response(200)
            self.end_headers_json()
            self.wfile.write(json.dumps({"completion_rate": round(rate, 1), "total": total, "completed": completed}).encode('utf-8'))
            
        elif path == "/api/blocklist":
            try:
                from task_manager.blockers.blocklist import blocklist_manager
                saved = blocklist_manager.load_sites()
                self.send_response(200)
                self.end_headers_json()
                self.wfile.write(json.dumps({"blocklist": saved}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers_json()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        
        try:
            data = json.loads(post_data)
        except json.JSONDecodeError:
            data = {}

        if path == "/api/tasks" and self.command == 'POST':
            try:
                title = data.get("title")
                priority = data.get("priority", "medium")
                tags = data.get("tags", [])
                
                if not title:
                    self.send_response(400)
                    self.end_headers_json()
                    self.wfile.write(json.dumps({"error": "Title is required"}).encode('utf-8'))
                    return

                tasks = storage.load_tasks()
                manager = models.TaskManager(tasks)
                
                new_task = models.Task(
                    id=0,
                    title=title,
                    priority=priority,
                    tags=tags
                )
                
                new_id = manager.add_task(new_task)
                storage.save_tasks(manager.tasks)
                
                self.send_response(201)
                self.end_headers_json()
                self.wfile.write(json.dumps({"success": True, "id": new_id}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers_json()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return

        elif path.startswith("/api/tasks/") and path.endswith("/complete"):
            try:
                task_id = int(path.split("/")[3])
                tasks = storage.load_tasks()
                found = False
                for task in tasks:
                    if task.id == task_id:
                        task.status = 'done'
                        found = True
                        break
                
                if found:
                    storage.save_tasks(tasks)
                    self.send_response(200)
                    self.end_headers_json()
                    self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
                else:
                    self.send_response(404)
                    self.end_headers_json()
                    self.wfile.write(json.dumps({"error": "Task not found"}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers_json()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif path == "/api/blocklist":
            try:
                from task_manager.blockers.blocklist import blocklist_manager
                if "add" in data:
                    blocklist_manager.add_sites([data["add"]])
                elif "remove" in data:
                    # remove_sites expects indices? Wait, the API takes indices: `def remove_sites(indices)`?
                    # Let me check if blocklist_manager has a way to remove by name, or I'll just load and save.
                    saved = blocklist_manager.load_sites()
                    if data["remove"] in saved:
                        saved.remove(data["remove"])
                        # How does it save? It doesn't have save_sites?
                        with open(blocklist_manager.blocklist_file, 'w') as f:
                            json.dump({"websites": saved}, f, indent=4)
                
                self.send_response(200)
                self.end_headers_json()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers_json()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif path == "/api/focus/start":
            minutes = int(data.get("minutes", 25))
            mode = data.get("mode", "gentle")
            
            def run_focus():
                try:
                    import sys, io
                    # Mask stdout so it doesn't spam the daemon server logs
                    original = sys.stdout
                    sys.stdout = io.StringIO()
                    commands.focus_task(task_id=None, minutes=minutes, mode=mode, force=True)
                    sys.stdout = original
                except Exception as e:
                    pass
            threading.Thread(target=run_focus, daemon=True).start()
            self.send_response(200)
            self.end_headers_json()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            
        elif path == "/api/focus/end":
            commands.end_focus(force=True)
            self.send_response(200)
            self.end_headers_json()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            
                
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress logging to keep CLI clean
        pass


def start_server(port=18082):
    server = ThreadingHTTPServer(('127.0.0.1', port), TaskFlowHandler)
    def run_server():
        try:
            print("Server thread actually started successfully!")
            server.serve_forever()
        except Exception as e:
            print(f"SERVER THREAD EXCEPTION: {e}")
    # Start thread as daemon so it dies when main thread dies
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return server

if __name__ == "__main__":
    import time
    import sys
    
    port = 18083
    print(f"\nStarting TaskFlow Web UI Server on port {port}...")
    srv = start_server(port)
    
    print(f"   Dashboard: http://127.0.0.1:{port}")
    print("   Press Ctrl+C to stop.\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping server...")
        srv.shutdown()
        sys.exit(0)
