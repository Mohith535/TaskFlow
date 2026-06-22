import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from urllib.parse import urlparse, parse_qs
from task_manager import storage, commands
from task_manager.commands import normalize_priority
from task_manager.web_ui import HTML_TEMPLATE
from task_manager import models

# D7-03: ThreadingHTTPServer runs each request in its own thread, and task mutations are
# read-modify-write against tasks.json. Serialise all writes so concurrent requests can't
# lose updates (atomic file replace prevents corruption, not lost writes).
_WRITE_LOCK = threading.Lock()


def _computed_task_fields(t):
    """CODE-HEALTH single source of truth: derive the values the dashboard used to
    re-implement in JS (pressure level, duration→minutes, priority tier, overdue) here in
    Python and ship them in the task payload. Time-relative fields (pressure_level, is_overdue)
    are recomputed on every fetch — the dashboard re-polls, so the JS consumes, never derives."""
    from task_manager import commands as _c
    from datetime import datetime as _dt
    try:
        pl = _c.get_pressure_level(t)
    except Exception:
        pl = 0
    dur = (getattr(t, 'duration', None) or '').lower()
    is_overdue = False
    try:
        if getattr(t, 'deadline', None) and not getattr(t, 'completed', False):
            dl = _dt.fromisoformat(t.deadline)
            if dl.tzinfo is not None:
                dl = dl.replace(tzinfo=None)
            is_overdue = dl < _dt.now()
    except Exception:
        is_overdue = False
    return {
        "pressure_level": pl,
        "duration_minutes": _c.DURATION_MINUTES.get(dur) if dur else None,
        "priority_tier": _c._priority_tier(t),
        "is_overdue": is_overdue,
    }


class TaskFlowHandler(BaseHTTPRequestHandler):
    def end_headers_json(self):
        # D7-01: the UI is served same-origin by this very server, so NO CORS grant is needed.
        # A wildcard Access-Control-Allow-Origin would let ANY website you visit read or delete
        # your local tasks from your browser. Omitting it keeps the local API private.
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

    def do_OPTIONS(self):
        # D7-01: respond 200 WITHOUT Allow-Origin so third-party pages can't preflight their
        # way into the local API. Same-origin requests never need a preflight.
        self.send_response(200)
        self.send_header('Allow', 'GET, POST, PATCH, DELETE, OPTIONS')
        self.end_headers()

    # --- Security guards (SEC-02 CSRF / SEC-07 DNS-rebinding) ---
    _LOCAL_HOSTNAMES = ("127.0.0.1", "localhost", "::1", "")

    def _host_is_local(self):
        """SEC-07: the Host header must name this loopback server (blocks DNS rebinding)."""
        host = (self.headers.get('Host') or '').strip().lower()
        if host.startswith('['):           # [::1]:port
            host = host[1:].split(']')[0]
        else:
            host = host.split(':')[0]
        return host in self._LOCAL_HOSTNAMES

    def _origin_is_local(self):
        """SEC-02: on mutations, any Origin/Referer present must be our own host (CSRF defense)."""
        for h in ('Origin', 'Referer'):
            v = self.headers.get(h)
            if not v:
                continue
            try:
                hn = (urlparse(v).hostname or '').lower()
            except Exception:
                hn = 'foreign'
            if hn not in ('127.0.0.1', 'localhost', '::1'):
                return False
        return True

    def _guard(self, mutating=False):
        """Return True (and send 403) if the request must be rejected. SEC-02 / SEC-07."""
        if not self._host_is_local():
            self.send_response(403)
            self.end_headers()
            return True
        if mutating and not self._origin_is_local():
            self.send_response(403)
            self.end_headers()
            return True
        return False

    # --- Enrichment helpers (E13) ---
    def _send_json(self, code, payload):
        self.send_response(code)
        self.end_headers_json()
        self.wfile.write(json.dumps(payload).encode('utf-8'))

    def _read_body(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
        except (TypeError, ValueError):
            content_length = 0
        raw = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _find_task(self, tasks, task_id):
        return next((t for t in tasks if t.id == task_id), None)

    def _sync_counters(self, task):
        """Keep links_count / checklist_total / checklist_done in sync (Rule #2)."""
        task.links = getattr(task, 'links', None) or []
        task.checklist = getattr(task, 'checklist', None) or []
        task.links_count = len(task.links)
        task.checklist_total = len(task.checklist)
        task.checklist_done = sum(1 for x in task.checklist if x.get('done'))

    def _path_payload(self, regenerate=False):
        """Build the S10 Daily Execution Path payload for the UI (GET/POST /api/path)."""
        from task_manager import commands as _cmds
        from datetime import datetime as _dt
        cfg = storage.storage.load_config()
        today = _dt.now().strftime('%Y-%m-%d')
        total = None
        if regenerate or cfg.get('path_generated_date') != today or not cfg.get('path_sections'):
            sections, total = _cmds.generate_and_persist_path()
            cfg = storage.storage.load_config()
        else:
            sections = cfg.get('path_sections') or {}

        tasks = storage.load_tasks()
        by_id = {t.id: t for t in tasks}

        def pack(idlist):
            out = []
            for i in idlist:
                t = by_id.get(i)
                if not t:
                    continue
                out.append({
                    "id": t.id,
                    "title": t.title,
                    "priority": t.priority,
                    "duration": t.duration,
                    "deadline": t.deadline,
                    "deadline_type": getattr(t, 'deadline_type', None),
                    "completed": t.completed,
                    "tags": getattr(t, 'tags', None) or [],
                    "planned_slot": getattr(t, 'planned_slot', None),
                    **_computed_task_fields(t),
                })
            return out

        keys = ("prime", "secondary", "low_effort", "unscheduled")
        packed = {k: pack(sections.get(k, []) if isinstance(sections, dict) else []) for k in keys}
        dmin = _cmds.DURATION_MINUTES

        def sec_min(k):
            return sum(dmin.get((it.get("duration") or "").lower(), 30) for it in packed[k])

        section_minutes = {k: sec_min(k) for k in keys}
        if total is None:
            total = section_minutes["prime"] + section_minutes["secondary"] + section_minutes["low_effort"]

        # Issue 2: forward-looking overdue candidates so the UI never shows a false
        # "nothing to do" when there's a backlog. Single source = commands.overdue_candidates.
        cand_tasks = _cmds.overdue_candidates(tasks, 5)
        overdue_packed = [{
            "id": t.id, "title": t.title, "priority": t.priority, "duration": t.duration,
            "deadline": t.deadline, "deadline_type": getattr(t, 'deadline_type', None),
            **_computed_task_fields(t),
        } for t in cand_tasks]
        overdue_total = sum(
            1 for t in tasks
            if (not t.completed and not getattr(t, 'dropped_at', None) and not getattr(t, 'offloaded_at', None)
                and _computed_task_fields(t).get('is_overdue'))
        )

        return {
            "generated_date": cfg.get('path_generated_date'),
            "sections": packed,
            "section_minutes": section_minutes,
            "total_minutes": total,
            "adherence": cfg.get('path_adherence_today'),
            "day_note": cfg.get('path_day_note'),
            "day_mode": cfg.get('path_day_mode'),
            "overdue_candidates": overdue_packed,
            "overdue_total": overdue_total,
            "evening": _dt.now().hour >= 18,
            "has_path": bool(packed["prime"] or packed["secondary"] or packed["low_effort"]),
        }

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if self._guard():   # SEC-07: reject foreign Host (DNS-rebinding)
            return

        if path == "/":
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            # SEC-01: CSP blocks the XSS *exfiltration* channel even if a payload slips escaping —
            # connect-src/img-src 'self' means a script can't phone home to evil.com.
            self.send_header('Content-Security-Policy',
                             "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                             "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                             "font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'")
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8', errors='replace'))


        elif path == "/api/tasks":
            tasks = storage.load_tasks()
            # Return ALL fields (including Phase 1 fields) for pending tasks
            pending_tasks = [
                {
                    "id": t.id,
                    "title": t.title,
                    "priority": t.priority,
                    "tags": t.tags,
                    "notes": t.notes,
                    "completed": t.completed,
                    "created_at": t.created_at,
                    # Phase 1 new fields
                    "duration": getattr(t, 'duration', None),
                    "deadline": getattr(t, 'deadline', None),
                    "deadline_type": getattr(t, 'deadline_type', None),
                    "postpone_count": getattr(t, 'postpone_count', 0),
                    "postpone_history": getattr(t, 'postpone_history', []),
                    "reminder_time": getattr(t, 'reminder_time', None),
                    "reminder_time_2": getattr(t, 'reminder_time_2', None),
                    "reminder_fired": getattr(t, 'reminder_fired', False),
                    "reminder_fired_2": getattr(t, 'reminder_fired_2', False),
                    "reminder_dismissed": getattr(t, 'reminder_dismissed', False),
                    "dropped_at": getattr(t, 'dropped_at', None),
                    "offloaded_at": getattr(t, 'offloaded_at', None),
                    "offload_note": getattr(t, 'offload_note', None),
                    "executed_late": getattr(t, 'executed_late', None),
                    # Event system fields
                    "mission_type": getattr(t, 'mission_type', 'Task'),
                    "date": getattr(t, 'date', None),
                    "start_time": getattr(t, 'start_time', None),
                    "end_time": getattr(t, 'end_time', None),
                    "status": getattr(t, 'status', None),
                    # Enrichment fields (E13)
                    "description": getattr(t, 'description', None),
                    "links": getattr(t, 'links', []) or [],
                    "checklist": getattr(t, 'checklist', []) or [],
                    "description_updated_at": getattr(t, 'description_updated_at', None),
                    "links_count": getattr(t, 'links_count', 0),
                    "checklist_total": getattr(t, 'checklist_total', 0),
                    "checklist_done": getattr(t, 'checklist_done', 0),
                    # CODE-HEALTH single-source: server-computed values (JS consumes, never re-derives)
                    **_computed_task_fields(t),
                }
                for t in tasks if getattr(t, 'dropped_at', None) is None and getattr(t, 'offloaded_at', None) is None
            ]
            self.send_response(200)
            self.end_headers_json()
            self.wfile.write(json.dumps({"tasks": pending_tasks}).encode('utf-8'))

        elif path == "/api/debug_tasks":
            tasks = storage.load_tasks()
            self.send_response(200)
            self.end_headers_json()
            self.wfile.write(json.dumps({"len_tasks": len(tasks), "file": str(storage.TaskStorage().tasks_file)}).encode('utf-8'))

        elif path == "/api/stats":
            tasks = storage.load_tasks()
            total = len(tasks)
            completed = sum(1 for t in tasks if t.completed)
            rate = (completed / total * 100) if total > 0 else 0
            
            self.send_response(200)
            self.end_headers_json()
            self.wfile.write(json.dumps({"completion_rate": round(rate, 1), "total": total, "completed": completed}).encode('utf-8'))
            
        elif path == "/api/timeline":
            mapping = storage.load_timeline()
            self.send_response(200)
            self.end_headers_json()
            self.wfile.write(json.dumps(mapping).encode('utf-8'))

        elif path == "/api/recovery-status":
            try:
                state = storage.storage.load_recovery_state()
                self.send_response(200)
                self.end_headers_json()
                self.wfile.write(json.dumps(state).encode('utf-8'))
            except Exception as e:
                self.send_response(200)
                self.end_headers_json()
                self.wfile.write(json.dumps({"active": False}).encode('utf-8'))

        elif path == "/api/recovery-preview":
            try:
                from task_manager import commands as _cmds
                preview = _cmds.select_recovery_tasks()
                self.send_response(200)
                self.end_headers_json()
                self.wfile.write(json.dumps({"preview_tasks": [t.to_dict() for t in preview]}).encode('utf-8'))
            except Exception:
                self.send_response(200)
                self.end_headers_json()
                self.wfile.write(json.dumps({"preview_tasks": []}).encode('utf-8'))

        elif path == "/api/tasks/completed-today":
            try:
                from datetime import datetime as _dt
                today = _dt.now().strftime('%Y-%m-%d')
                tasks = storage.load_tasks()
                count = sum(1 for t in tasks if t.completed and getattr(t, 'completed_at', None) and str(t.completed_at).startswith(today))
                self.send_response(200)
                self.end_headers_json()
                self.wfile.write(json.dumps({"count": count}).encode('utf-8'))
            except Exception:
                self.send_response(200)
                self.end_headers_json()
                self.wfile.write(json.dumps({"count": 0}).encode('utf-8'))

        elif path == "/api/stats-full":
            # Extended stats including overdue + deferred counts
            tasks = storage.load_tasks()
            from datetime import datetime
            now = datetime.now()
            total = len(tasks)
            completed = sum(1 for t in tasks if t.completed)
            pending = [t for t in tasks if not t.completed]
            overdue = sum(1 for t in pending if t.deadline and datetime.fromisoformat(t.deadline) < now)
            deferred = sum(1 for t in pending if getattr(t, 'postpone_count', 0) >= 2)
            rate = (completed / total * 100) if total > 0 else 0
            self.send_response(200)
            self.end_headers_json()
            self.wfile.write(json.dumps({
                "completion_rate": round(rate, 1),
                "total": total,
                "completed": completed,
                "pending": len(pending),
                "overdue": overdue,
                "deferred": deferred
            }).encode('utf-8'))

        elif path == "/api/stats/weekly":
            # S12-F: weekly Time Integrity aggregates (+ streak + recent recovery)
            try:
                from task_manager import commands as _cmds
                _cmds.ensure_daily_summaries()
                summaries = storage.storage.load_daily_summaries()
                w = _cmds.compute_weekly_stats(summaries) or {}
                cfg = storage.storage.load_config()
                w['execution_streak'] = cfg.get('execution_streak', 0)
                rlog = []
                try:
                    if storage.storage.recovery_log_file.exists():
                        with open(storage.storage.recovery_log_file) as rf:
                            rlog = json.load(rf)
                except Exception:
                    rlog = []
                w['recovery_history'] = (rlog or [])[-5:][::-1]
                self._send_json(200, w)
            except Exception as e:
                self._send_json(200, {"error": str(e)})

        elif path == "/api/stats/daily-summaries":
            # S12-F: last 7 computed daily summaries
            try:
                from task_manager import commands as _cmds
                _cmds.ensure_daily_summaries()
                summaries = storage.storage.load_daily_summaries()
                self._send_json(200, {"summaries": summaries[-7:]})
            except Exception:
                self._send_json(200, {"summaries": []})

        elif path == "/api/stats/day-of-week":
            # S14-F: per-weekday performance aggregates for the Analytics "DAY OF WEEK" card
            try:
                from task_manager import commands as _cmds
                _cmds.ensure_daily_summaries()
                summaries = storage.storage.load_daily_summaries()
                self._send_json(200, _cmds.compute_day_of_week_stats(summaries))
            except Exception as e:
                self._send_json(200, {"by_day": {}, "best_day": None, "worst_day": None,
                                      "best_day_name": None, "worst_day_name": None,
                                      "best_day_avg_tis": None, "worst_day_avg_tis": None,
                                      "recommendation": "", "error": str(e)})

        elif path == "/api/focus_state":
            try:
                from task_manager.commands import focus_manager
                status = focus_manager.get_focus_status()
                # e.g. {"focus_active": True, "task_id": X, "task_title": "...", "minutes_left": 25, ...}
                self.send_response(200)
                self.end_headers_json()
                self.wfile.write(json.dumps(status).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers_json()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            
        elif path == "/api/focus-status":
            # S11-F: focus lock status for the UI (active / task_id / ends_at / queued_count)
            try:
                from task_manager import commands as _cmds
                self._send_json(200, _cmds.focus_status_payload())
            except Exception:
                self._send_json(200, {"active": False, "task_id": None, "ends_at": None, "queued_count": 0})

        elif path == "/api/focus/preflight":
            # Honest answer for the Focus Setup modal: can strict blocking actually engage?
            # (Editing the hosts file / killing apps needs Administrator on Windows.)
            try:
                from task_manager.system_detector import SystemDetector
                self._send_json(200, {"is_admin": bool(SystemDetector.is_admin()),
                                      "platform": SystemDetector.get_os()})
            except Exception:
                self._send_json(200, {"is_admin": False, "platform": "unknown"})

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
            
        elif path == "/api/path":
            # S10-F: current day's Daily Execution Path (auto-generates if stale)
            try:
                self._send_json(200, self._path_payload(regenerate=False))
            except Exception as e:
                self._send_json(200, {
                    "generated_date": None,
                    "sections": {"prime": [], "secondary": [], "low_effort": [], "unscheduled": []},
                    "section_minutes": {"prime": 0, "secondary": 0, "low_effort": 0, "unscheduled": 0},
                    "total_minutes": 0, "adherence": None, "error": str(e),
                    "overdue_candidates": [], "overdue_total": 0, "evening": False, "has_path": False
                })

        elif path.startswith("/static/"):
            try:
                import os
                file_path = path[8:].lstrip('/\\')
                static_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), 'static'))
                full_path = os.path.realpath(os.path.join(static_dir, file_path))
                # SEC-05: containment — the resolved path must stay inside static_dir.
                # realpath + commonpath defeats ../ traversal AND absolute/drive paths.
                if os.path.commonpath([static_dir, full_path]) != static_dir:
                    self.send_response(404)
                    self.end_headers()
                    return

                if os.path.exists(full_path) and os.path.isfile(full_path):
                    self.send_response(200)
                    if full_path.endswith('.js'):
                        self.send_header('Content-Type', 'application/javascript')
                    elif full_path.endswith('.css'):
                        self.send_header('Content-Type', 'text/css')
                    self.end_headers()
                    with open(full_path, 'rb') as f:
                        self.wfile.write(f.read())
                else:
                    self.send_response(404)
                    self.end_headers()
            except Exception:
                self.send_response(404)
                self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        with _WRITE_LOCK:   # D7-03: serialise writes
            self._handle_POST()

    def _handle_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if self._guard(mutating=True):   # SEC-02/07: block cross-site + foreign-Host writes
            return

        try:
            content_length = int(self.headers.get('Content-Length', 0))
        except (TypeError, ValueError):
            content_length = 0
        post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        
        try:
            data = json.loads(post_data)
        except json.JSONDecodeError:
            data = {}

        if path == "/api/tasks" and self.command == 'POST':
            try:
                title = data.get("title")
                priority_raw = data.get("priority", "medium")
                priority = normalize_priority(priority_raw)
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

        elif path == "/api/tasks/dump" and self.command == 'POST':
            try:
                title = data.get("title", "").strip()
                if not title:
                    self.send_response(400)
                    self.end_headers_json()
                    self.wfile.write(json.dumps({"error": "Empty title"}).encode('utf-8'))
                    return
                    
                from task_manager import commands
                task_dict = commands.dump_task(title)
                if task_dict:
                    self.send_response(201)
                    self.end_headers_json()
                    self.wfile.write(json.dumps({"success": True, "task": task_dict}).encode('utf-8'))
                else:
                    self.send_response(500)
                    self.end_headers_json()
                    self.wfile.write(json.dumps({"error": "Failed to dump task"}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers_json()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return

        elif path == "/api/timeline" and self.command == 'POST':
            try:
                # Expect dict {"mapping": {"1": "2026-03-31_prime"}}
                mapping = data.get("mapping", {})
                storage.save_timeline(mapping)
                self.send_response(200)
                self.end_headers_json()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers_json()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return
            
        elif (path == "/api/focus_end" or path == "/api/focus/end") and self.command == 'POST':
            from task_manager import commands
            try:
                commands.end_focus(force=True)        # graceful end (blocker cleanup, queue flush)
            except Exception:
                pass
            # GUARANTEE the session is gone in memory AND on disk, regardless of what end_focus
            # did — otherwise check_focus() reloads the old session and the overlay resurrects.
            try:
                commands.time_tracker.active_session = None
                commands.time_tracker.start_time = None
                commands.time_tracker._save_state({'active_session': None, 'start_time': None})
            except Exception:
                pass
            self._send_json(200, {"success": True})
            return

        elif path == "/api/focus/pause" and self.command == 'POST':
            try:
                from task_manager import commands
                commands.time_tracker.pause_focus()
                self.send_response(200)
                self.end_headers_json()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers_json()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return

        elif path == "/api/focus/resume" and self.command == 'POST':
            try:
                from task_manager import commands
                commands.time_tracker.resume_focus()
                self.send_response(200)
                self.end_headers_json()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers_json()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return

        elif path == "/api/focus/complete" and self.command == 'POST':
            try:
                from task_manager import commands
                efficiency_score = data.get("efficiency_score", 0)
                time_saved = data.get("time_saved", 0)
                time_used = data.get("time_used", 0)
                
                # Update task in storage via unified complete_task (triggers Dopamine Engine)
                status = commands.focus_manager.get_focus_status()
                dopamine = {}
                if status and status.get("focus_active"):
                    task_id = status.get("task_id")
                    if task_id:
                        # Generate dopamine via unified engine (marks complete + tracks streak)
                        result = commands.complete_task(task_id)
                        if isinstance(result, dict):
                            dopamine = result
                        
                        # Also track the focus time (this was handled before mark_complete)
                        tasks = storage.load_tasks()
                        for task in tasks:
                            if task.id == task_id:
                                task.add_focus_minutes(time_used)
                                storage.save_tasks(tasks)
                                break

                # Sync focus state
                try:
                    commands.complete_focus(efficiency_score, time_saved, time_used)
                except Exception as ex:
                    try:
                        commands.time_tracker.end_focus()
                        commands.time_tracker._save_state({'active_session': None, 'start_time': None})
                    except: pass

                self.send_response(200)
                self.end_headers_json()
                response = {"success": True}
                response.update(dopamine)
                self.wfile.write(json.dumps(response).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers_json()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return
            
        elif path == "/api/focus/next" and self.command == 'GET':
            try:
                from task_manager import commands
                limit = int(parse_qs(parsed.query).get('limit', ['3'])[0])
                targets = commands.get_momentum_targets(limit=limit)
                self.send_response(200)
                self.end_headers_json()
                self.wfile.write(json.dumps({"targets": targets}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers_json()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return

        elif path.startswith("/api/tasks/") and path.endswith("/complete"):
            try:
                task_id = int(path.split("/")[3])
                from task_manager import commands
                dopamine = commands.complete_task(task_id)
                
                if dopamine is not False:
                    self.send_response(200)
                    self.end_headers_json()
                    response_data = {"success": True}
                    if isinstance(dopamine, dict):
                        response_data.update(dopamine)
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                else:
                    self.send_response(404)
                    self.end_headers_json()
                    self.wfile.write(json.dumps({"error": "Task not found"}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers_json()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif path.startswith("/api/tasks/") and path.endswith("/delete"):
            try:
                task_id = int(path.split("/")[3])
                tasks = storage.load_tasks()
                manager = models.TaskManager(tasks)
                if manager.delete_task(task_id):
                    storage.save_tasks(manager.tasks)
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

        elif path.startswith("/api/tasks/") and path.endswith("/postpone"):
            try:
                task_id = int(path.split("/")[3])
                increment = data.get("increment", "+1h")
                tasks = storage.load_tasks()
                task = None
                for t in tasks:
                    if t.id == task_id:
                        task = t
                        break
                if not task:
                    self.send_response(404)
                    self.end_headers_json()
                    self.wfile.write(json.dumps({"error": "Task not found"}).encode('utf-8'))
                    return
                from datetime import datetime, timedelta
                now = datetime.now()
                # Calculate new deadline based on increment
                increment_map = {
                    "+15m": timedelta(minutes=15),
                    "+1h": timedelta(hours=1),
                    "+3h": timedelta(hours=3),
                    "tomorrow": None  # Special case
                }
                if increment == "tomorrow":
                    tomorrow = now + timedelta(days=1)
                    new_deadline = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
                elif increment in increment_map:
                    base = datetime.fromisoformat(task.deadline) if task.deadline else now
                    if base < now:
                        base = now  # Don't postpone from an overdue date
                    new_deadline = base + increment_map[increment]
                else:
                    try:
                        # Attempt to parse as ISO string
                        new_deadline = datetime.fromisoformat(increment.replace('Z', '+00:00'))
                    except ValueError:
                        new_deadline = now + timedelta(hours=1)
                
                reason = data.get("reason", "").strip()
                history_entry = json.dumps({
                    "date": now.isoformat(),
                    "increment": increment,
                    "reason": reason
                })
                
                task.deadline = new_deadline.isoformat()
                task.postpone_count += 1
                task.postpone_history.append(history_entry)
                storage.save_tasks(tasks)
                
                self.send_response(200)
                self.end_headers_json()
                self.wfile.write(json.dumps({
                    "success": True,
                    "postpone_count": task.postpone_count,
                    "new_deadline": task.deadline
                }).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers_json()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif path.startswith("/api/tasks/") and path.endswith("/offload"):
            try:
                task_id = int(path.split("/")[3])
                note = data.get("note", "Delegated")
                tasks = storage.load_tasks()
                task = None
                for t in tasks:
                    if t.id == task_id:
                        task = t
                        break
                if not task:
                    self.send_response(404)
                    self.end_headers_json()
                    self.wfile.write(json.dumps({"error": "Task not found"}).encode('utf-8'))
                    return
                from datetime import datetime
                task.offloaded_at = datetime.now().isoformat()
                task.offload_note = note
                storage.save_tasks(tasks)
                
                self.send_response(200)
                self.end_headers_json()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
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
            task_id_raw = data.get("task_id") or data.get("id")
            try:
                task_id = int(task_id_raw) if task_id_raw is not None else None
            except (ValueError, TypeError):
                task_id = None
                
            minutes = int(data.get("minutes", 25))
            mode = data.get("mode", "gentle")
            block_sites = data.get("block_sites") or None      # strict-mode site list from the UI
            block_apps = data.get("block_apps") or None

            def run_focus():
                import sys, io
                # Import locally: other do_POST branches do `from task_manager import commands`,
                # which makes `commands` a function-local for ALL of do_POST — so the module-level
                # `commands` is shadowed and unbound on this path. (This was the real focus bug:
                # focus_task never ran, no session persisted, overlay died at the first poll.)
                from task_manager import commands as _cmds
                original = sys.stdout
                try:
                    sys.stdout = io.StringIO()   # keep focus_task's prints out of the server log
                    # open_ui=False: we ARE the web server — never re-launch the dashboard here.
                    _cmds.focus_task(task_id=task_id, minutes=minutes, mode=mode,
                                     block_sites=block_sites, block_apps=block_apps,
                                     force=True, open_ui=False)
                except Exception as e:
                    sys.stderr.write(f"[focus/start] {e}\n")
                finally:
                    sys.stdout = original        # always restore — never leave server stdout dead
            threading.Thread(target=run_focus, daemon=True).start()
            self.send_response(200)
            self.end_headers_json()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))

        elif path == "/api/path/generate" and self.command == 'POST':
            # S10-F: regenerate today's path on demand
            try:
                self._send_json(200, self._path_payload(regenerate=True))
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path == "/api/focus/queue" and self.command == 'POST':
            # S11-F: queue a task captured during an active focus session
            try:
                from task_manager import commands as _cmds
                n = _cmds.enqueue_focus_task(data)
                self._send_json(200, {"queued": True, "queue_length": n})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif path == "/api/recovery-activate" and self.command == 'POST':
            try:
                from datetime import datetime as _dt
                from task_manager import commands as _cmds
                reason = data.get("trigger_reason") or "D"
                state = storage.storage.load_recovery_state()
                if not state.get("active"):
                    sel = _cmds.select_recovery_tasks()
                    state["active"] = True
                    state["triggered_at"] = _dt.now().isoformat()
                    state["trigger_reason"] = reason
                    state["session_tasks"] = [t.id for t in sel]
                    state["completed_in_recovery"] = []
                    state["dismissed_at"] = None
                    state["last_checked_date"] = _dt.now().strftime('%Y-%m-%d')
                    storage.storage.save_recovery_state(state)
                self.send_response(200)
                self.end_headers_json()
                self.wfile.write(json.dumps({"success": True, "session_tasks": state.get("session_tasks", [])}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers_json()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif path == "/api/recovery-exit" and self.command == 'POST':
            try:
                from datetime import datetime as _dt
                state = storage.storage.load_recovery_state()
                if state.get("active"):
                    _comp = state.get("completed_in_recovery", []) or []
                    storage.storage.append_recovery_log({
                        "date": _dt.now().strftime('%Y-%m-%d'),
                        "triggered_at": state.get("triggered_at"),
                        "trigger_reason": state.get("trigger_reason"),
                        "session_tasks": state.get("session_tasks", []),
                        "tasks_completed": len(_comp),
                        "was_successful": len(_comp) >= 1,
                        "exited_at": _dt.now().isoformat()
                    })
                _was = len(state.get("completed_in_recovery", []) or []) >= 1
                state["active"] = False
                state["dismissed_at"] = _dt.now().isoformat()
                storage.storage.save_recovery_state(state)
                self.send_response(200)
                self.end_headers_json()
                self.wfile.write(json.dumps({"success": True, "was_successful": _was}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers_json()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif path.startswith("/api/reminder-dismiss/") and self.command == 'POST':
            try:
                task_id = int(path.split("/")[-1])
                tasks = storage.load_tasks()
                for task in tasks:
                    if task.id == task_id:
                        task.reminder_dismissed = True
                        break
                storage.save_tasks(tasks)
                self.send_response(200)
                self.end_headers_json()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers_json()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif path == "/api/tasks/create-full" and self.command == 'POST':
            # Create task with all Phase 1 fields (duration, deadline, deadline_type)
            try:
                title = data.get("title", "").strip()
                if not title:
                    self.send_response(400)
                    self.end_headers_json()
                    self.wfile.write(json.dumps({"error": "Title required"}).encode('utf-8'))
                    return

                import re
                
                priority_raw = data.get("priority", "medium")
                tags = data.get("tags", [])
                
                # Extract priority (!h, !m, !l)
                pri_match = re.search(r'!(h|m|l|hard|medium|low)\b', title, re.IGNORECASE)
                if pri_match:
                    p_val = pri_match.group(1).lower()
                    if p_val in ['h', 'hard']: priority_raw = 'high'
                    elif p_val in ['l', 'low']: priority_raw = 'low'
                    elif p_val in ['m', 'medium']: priority_raw = 'medium'
                    title = re.sub(r'!(h|m|l|hard|medium|low)\b', '', title, flags=re.IGNORECASE).strip()
                
                # Extract tags (#tag)
                tag_matches = re.findall(r'#(\w+)', title)
                if tag_matches:
                    tags.extend(tag_matches)
                    title = re.sub(r'#\w+', '', title).strip()
                    
                priority = normalize_priority(priority_raw)
                from task_manager.commands import normalize_duration as _norm_dur
                duration = _norm_dur(data.get("duration"))   # D1-01: sanitise web-supplied duration
                deadline = data.get("deadline")
                deadline_type = data.get("deadline_type")
                mission_type = data.get("mission_type", "Task")
                date = data.get("date")
                start_time = data.get("start_time")
                end_time = data.get("end_time")

                # Setup default reminder for Events
                reminder_time = None
                if mission_type == "Event" and deadline:
                    from datetime import datetime, timedelta
                    try:
                        dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                        # Default offset is 60 minutes, handle None from JSON
                        offset_minutes = data.get("reminder_offset", 60)
                        if offset_minutes is None:
                            offset_minutes = 60
                        if offset_minutes >= 0:
                            reminder_time = (dt - timedelta(minutes=offset_minutes)).isoformat()
                    except ValueError:
                        pass

                tasks = storage.load_tasks()
                manager = models.TaskManager(tasks)

                new_task = models.Task(
                    id=0,
                    title=title,
                    priority=priority,
                    tags=tags,
                    duration=duration,
                    deadline=deadline,
                    deadline_type=deadline_type,
                    mission_type=mission_type,
                    date=date,
                    start_time=start_time,
                    end_time=end_time,
                    reminder_time=reminder_time
                )

                # Enrichment on creation (E12/E13): description, links, checklist
                from datetime import datetime as _dt
                from task_manager.commands import detect_link_type
                desc = data.get("description")
                if desc:
                    new_task.description = desc
                    new_task.description_updated_at = _dt.now().isoformat()
                norm_links = []
                for ln in (data.get("links") or [])[:10]:
                    if isinstance(ln, str):
                        url, title, ltype = ln.strip(), None, None
                    else:
                        url = (ln.get("url") or "").strip()
                        title = ln.get("title") or None
                        ltype = ln.get("type")
                    if not url:
                        continue
                    norm_links.append({
                        "id": f"lnk_{len(norm_links)+1:03d}",
                        "type": ltype or detect_link_type(url),
                        "url": url,
                        "title": title,
                        "added_at": _dt.now().isoformat()
                    })
                new_task.links = norm_links
                new_task.links_count = len(norm_links)
                norm_chk = []
                for it in (data.get("checklist") or [])[:20]:
                    if isinstance(it, str):
                        text, done = it.strip(), False
                    else:
                        text = (it.get("text") or "").strip()
                        done = bool(it.get("done"))
                    if not text:
                        continue
                    norm_chk.append({
                        "id": f"chk_{len(norm_chk)+1:03d}",
                        "text": text,
                        "done": done,
                        "done_at": _dt.now().isoformat() if done else None
                    })
                new_task.checklist = norm_chk
                new_task.checklist_total = len(norm_chk)
                new_task.checklist_done = sum(1 for x in norm_chk if x.get("done"))

                new_id = manager.add_task(new_task)
                storage.save_tasks(manager.tasks)

                self.send_response(201)
                self.end_headers_json()
                self.wfile.write(json.dumps({"success": True, "id": new_id}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers_json()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif path.startswith("/api/tasks/") and path.endswith("/links") and self.command == 'POST':
            # POST /api/tasks/<id>/links  (E13)
            from datetime import datetime as _dt
            from task_manager.commands import detect_link_type
            parts = [p for p in path.split('/') if p]
            try:
                task_id = int(parts[2])
            except (ValueError, IndexError):
                self._send_json(400, {"error": "Invalid task id"})
                return
            tasks = storage.load_tasks()
            task = self._find_task(tasks, task_id)
            if not task:
                self._send_json(404, {"error": "Task not found"})
                return
            url = (data.get("url") or "").strip()
            if not url:
                self._send_json(400, {"error": "Missing 'url'"})
                return
            links = getattr(task, 'links', None) or []
            if len(links) >= 10:
                self._send_json(400, {"error": "Maximum 10 links reached"})
                return
            max_num = 0
            for l in links:
                try:
                    max_num = max(max_num, int(str(l.get('id', 'lnk_000')).replace('lnk_', '')))
                except ValueError:
                    pass
            links.append({
                "id": f"lnk_{max_num + 1:03d}",
                "type": data.get("type") or detect_link_type(url),
                "url": url,
                "title": data.get("title") or None,
                "added_at": _dt.now().isoformat()
            })
            task.links = links
            self._sync_counters(task)
            storage.save_tasks(tasks)
            self._send_json(200, task.to_dict())
            return

        elif path.startswith("/api/tasks/") and path.endswith("/checklist") and self.command == 'POST':
            # POST /api/tasks/<id>/checklist  (E13)
            parts = [p for p in path.split('/') if p]
            try:
                task_id = int(parts[2])
            except (ValueError, IndexError):
                self._send_json(400, {"error": "Invalid task id"})
                return
            tasks = storage.load_tasks()
            task = self._find_task(tasks, task_id)
            if not task:
                self._send_json(404, {"error": "Task not found"})
                return
            text = (data.get("text") or "").strip()
            if not text:
                self._send_json(400, {"error": "Missing 'text'"})
                return
            chk = getattr(task, 'checklist', None) or []
            if len(chk) >= 20:
                self._send_json(400, {"error": "Maximum 20 checklist items reached"})
                return
            max_num = 0
            for c in chk:
                try:
                    max_num = max(max_num, int(str(c.get('id', 'chk_000')).replace('chk_', '')))
                except ValueError:
                    pass
            chk.append({
                "id": f"chk_{max_num + 1:03d}",
                "text": text,
                "done": False,
                "done_at": None
            })
            task.checklist = chk
            self._sync_counters(task)
            storage.save_tasks(tasks)
            self._send_json(200, task.to_dict())
            return

        else:
            self.send_response(404)
            self.end_headers()

    def do_PATCH(self):
        with _WRITE_LOCK:   # D7-03: serialise writes
            self._handle_PATCH()

    def _handle_PATCH(self):
        parsed = urlparse(self.path)
        if self._guard(mutating=True):   # SEC-02/07
            return
        parts = [p for p in parsed.path.split('/') if p]
        if len(parts) >= 3 and parts[0] == 'api' and parts[1] == 'tasks':
            from datetime import datetime as _dt
            try:
                task_id = int(parts[2])
            except ValueError:
                self._send_json(400, {"error": "Invalid task id"})
                return
            tasks = storage.load_tasks()
            task = self._find_task(tasks, task_id)
            if not task:
                self._send_json(404, {"error": "Task not found"})
                return

            # PATCH /api/tasks/<id>  — general field edit (Edit System).
            # Whitelist editable fields only; id / created_at / completed_at / postpone_count
            # and all behavioral telemetry are intentionally NOT editable here.
            if len(parts) == 3:
                from task_manager.commands import normalize_duration as _norm_dur, parse_deadline as _parse_dl
                body = self._read_body()
                if 'title' in body:
                    nt = (body.get('title') or '').strip()
                    if nt:
                        task.title = nt[:500]
                if body.get('priority') is not None:
                    task.priority = normalize_priority(str(body.get('priority')))
                if 'tags' in body:
                    tags = body.get('tags') or []
                    if isinstance(tags, str):
                        tags = [s.strip() for s in tags.split(',') if s.strip()]
                    task.tags = [str(t).strip() for t in tags if str(t).strip()][:20]
                if 'duration' in body:
                    nd = _norm_dur(body.get('duration'))
                    if nd:
                        task.duration = nd
                if 'description' in body:
                    desc = body.get('description')
                    task.description = desc if desc else None
                    task.description_updated_at = _dt.now().isoformat()
                if 'scheduled_date' in body:
                    sd = body.get('scheduled_date')
                    task.scheduled_date = sd if sd else None
                deadline_touched = False
                if 'deadline' in body:
                    raw = body.get('deadline')
                    if not raw:
                        task.deadline = None
                        task.reminder_time = None
                        task.reminder_time_2 = None
                    else:
                        parsed = None
                        try:
                            parsed = _dt.fromisoformat(str(raw))
                        except Exception:
                            parsed = _parse_dl(str(raw))
                        if parsed:
                            task.deadline = parsed.isoformat()
                            deadline_touched = True
                if 'deadline_type' in body and task.deadline:
                    task.deadline_type = 'hard' if body.get('deadline_type') == 'hard' else 'soft'
                if not task.deadline:
                    task.deadline_type = None
                # Append client-supplied edit_history entry (APPEND-ONLY).
                entry = body.get('edit_history_entry')
                if isinstance(entry, dict):
                    if getattr(task, 'edit_history', None) is None:
                        task.edit_history = []
                    nova_on = storage.storage.load_config().get('nova_data_enabled', True) is not False
                    rt = entry.get("reason_text")
                    task.edit_history.append({
                        "timestamp": entry.get("timestamp") or _dt.now().isoformat(),
                        "field": str(entry.get("field", "edit"))[:40],
                        "old_value": entry.get("old_value"),
                        "new_value": entry.get("new_value"),
                        "reason_code": entry.get("reason_code") if nova_on else None,
                        "reason_text": (str(rt)[:1000] if (rt and nova_on) else None),
                    })
                if deadline_touched and task.deadline:
                    try:
                        commands.calculate_reminder_time(task)
                    except Exception:
                        pass
                self._sync_counters(task)
                storage.save_tasks(tasks)
                self._send_json(200, {**task.to_dict(), **_computed_task_fields(task)})
                return

            # PATCH /api/tasks/<id>/description
            if len(parts) == 4 and parts[3] == 'description':
                body = self._read_body()
                if 'description' not in body:
                    self._send_json(400, {"error": "Missing 'description'"})
                    return
                desc = body.get('description')
                task.description = desc if desc else None
                task.description_updated_at = _dt.now().isoformat()
                self._sync_counters(task)
                storage.save_tasks(tasks)
                self._send_json(200, task.to_dict())
                return

            # PATCH /api/tasks/<id>/checklist/<chk_id>/toggle
            if len(parts) == 6 and parts[3] == 'checklist' and parts[5] == 'toggle':
                chk_id = parts[4]
                item = next((c for c in (getattr(task, 'checklist', None) or []) if c.get('id') == chk_id), None)
                if not item:
                    self._send_json(404, {"error": "Checklist item not found"})
                    return
                if item.get('done'):
                    item['done'] = False
                    item['done_at'] = None
                else:
                    item['done'] = True
                    item['done_at'] = _dt.now().isoformat()
                self._sync_counters(task)
                storage.save_tasks(tasks)
                self._send_json(200, task.to_dict())
                return

        self._send_json(404, {"error": "Not found"})

    def do_DELETE(self):
        with _WRITE_LOCK:   # D7-03: serialise writes
            self._handle_DELETE()

    def _handle_DELETE(self):
        parsed = urlparse(self.path)
        if self._guard(mutating=True):   # SEC-02/07
            return
        parts = [p for p in parsed.path.split('/') if p]
        if len(parts) == 5 and parts[0] == 'api' and parts[1] == 'tasks':
            try:
                task_id = int(parts[2])
            except ValueError:
                self._send_json(400, {"error": "Invalid task id"})
                return
            tasks = storage.load_tasks()
            task = self._find_task(tasks, task_id)
            if not task:
                self._send_json(404, {"error": "Task not found"})
                return

            # DELETE /api/tasks/<id>/links/<link_id>  (IDs are permanent; no re-index, Rule #3)
            if parts[3] == 'links':
                link_id = parts[4]
                links = getattr(task, 'links', None) or []
                new_links = [l for l in links if l.get('id') != link_id]
                if len(new_links) == len(links):
                    self._send_json(404, {"error": "Link not found"})
                    return
                task.links = new_links
                self._sync_counters(task)
                storage.save_tasks(tasks)
                self._send_json(200, task.to_dict())
                return

            # DELETE /api/tasks/<id>/checklist/<chk_id>
            if parts[3] == 'checklist':
                chk_id = parts[4]
                chk = getattr(task, 'checklist', None) or []
                new_chk = [c for c in chk if c.get('id') != chk_id]
                if len(new_chk) == len(chk):
                    self._send_json(404, {"error": "Checklist item not found"})
                    return
                task.checklist = new_chk
                self._sync_counters(task)
                storage.save_tasks(tasks)
                self._send_json(200, task.to_dict())
                return

        self._send_json(404, {"error": "Not found"})

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
    # Safety net: if a previous run died (taskkill/crash) with the Windows system proxy still
    # pointed at our now-dead local filter, restore the user's original proxy before doing anything.
    try:
        from task_manager.blockers.proxy_filter import ProxyFilter
        ProxyFilter.rollback_if_stale()
    except Exception:
        pass
    # Likewise scrub any leftover TaskFlow hosts-file block from a crashed prior session.
    try:
        import sys as _sys
        if _sys.platform == "win32":
            from task_manager.blockers.windows import clear_stale_taskflow_hosts
            clear_stale_taskflow_hosts()
    except Exception:
        pass
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
