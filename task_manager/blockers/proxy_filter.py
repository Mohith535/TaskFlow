"""DoH-proof website blocking via a local filtering proxy (Windows).

Why this exists: strict *hosts-file* blocking is silently bypassed by browsers using Secure DNS
(DoH) — they resolve domains over their own encrypted DNS and never consult the OS hosts file.
A local forwarding proxy, by contrast, sees the destination HOSTNAME (the HTTPS `CONNECT` target
or the plain-HTTP `Host:` header) no matter how DNS was resolved, so it can block reliably
*without asking the user to change any browser setting*. It also needs **no administrator rights**
(the per-user proxy setting + a loopback listener are both unprivileged).

We never decrypt anything: for HTTPS we only read the `CONNECT host:port` line, then either refuse
(blocked) or blindly relay bytes (allowed). No TLS interception, no content inspection.

SAFETY (the load-bearing part): pointing the Windows system proxy at us affects every app, so it
MUST come back. We (1) save the prior setting, (2) restore it on stop()/atexit, and (3) persist
the saved setting to ~/.taskflow/proxy_state.json so a *later* run can roll it back even after a
hard crash/taskkill — see `rollback_if_stale`, which the server calls on startup. A dead proxy can
therefore never strand the user's connection past the next launch.
"""

from __future__ import annotations

import atexit
import json
import select
import socket
import socketserver
import sys
import threading
from pathlib import Path

_BLOCK_PAGE = (
    b"HTTP/1.1 403 Forbidden\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n\r\n"
    b"<html><body style='font-family:system-ui,sans-serif;background:#0D1117;color:#E6EDF3;"
    b"text-align:center;padding-top:16vh'><div style='font-size:42px'>&#128737;</div>"
    b"<h1 style='font-weight:600'>Blocked while you focus</h1>"
    b"<p style='color:#8B949E'>TaskFlow has this site paused. End the focus session to reopen it.</p>"
    b"</body></html>"
)


def _domain_blocked(host: str, blocked) -> bool:
    """True if `host` is, or is a subdomain of, any blocked domain (www. is ignored)."""
    host = (host or "").lower().strip().strip("[]").split(":")[0]
    if not host:
        return False
    for b in blocked or []:
        b = (b or "").lower().strip()
        b = b.replace("http://", "").replace("https://", "").replace("www.", "").split("/")[0].split(":")[0]
        if not b:
            continue
        if host == b or host == "www." + b or host.endswith("." + b):
            return True
    return False


class _ProxyHandler(socketserver.BaseRequestHandler):
    def handle(self):
        c = self.request
        try:
            c.settimeout(15)
            buf = b""
            while b"\r\n" not in buf:
                chunk = c.recv(4096)
                if not chunk:
                    return
                buf += chunk
                if len(buf) > 65536:
                    return
            first = buf.split(b"\r\n", 1)[0].decode("latin1", "replace")
            parts = first.split()
            if len(parts) < 2:
                return
            method, target = parts[0].upper(), parts[1]
            blocked = getattr(self.server, "blocked", [])

            if method == "CONNECT":                      # HTTPS tunnel
                host = target.rsplit(":", 1)[0].strip("[]")
                try:
                    port = int(target.rsplit(":", 1)[1])
                except Exception:
                    port = 443
                if _domain_blocked(host, blocked):
                    c.sendall(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n")
                    return
                self._tunnel(c, host, port)
            else:                                        # plain HTTP
                host = ""
                if "://" in target:
                    host = target.split("://", 1)[1].split("/", 1)[0]
                else:
                    for ln in buf.split(b"\r\n"):
                        if ln.lower().startswith(b"host:"):
                            host = ln.split(b":", 1)[1].decode("latin1", "replace").strip()
                            break
                if _domain_blocked(host, blocked):
                    c.sendall(_BLOCK_PAGE)
                    return
                self._forward_plain(c, host, buf)
        except Exception:
            pass
        finally:
            try:
                c.close()
            except Exception:
                pass

    def _tunnel(self, c, host, port):
        try:
            up = socket.create_connection((host, port), timeout=10)
        except Exception:
            try:
                c.sendall(b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n")
            except Exception:
                pass
            return
        try:
            c.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            self._relay(c, up)
        finally:
            try:
                up.close()
            except Exception:
                pass

    def _forward_plain(self, c, host, buf):
        port = 80
        if ":" in host:
            host, p = host.rsplit(":", 1)
            try:
                port = int(p)
            except Exception:
                port = 80
        try:
            up = socket.create_connection((host, port), timeout=10)
        except Exception:
            try:
                c.sendall(b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n")
            except Exception:
                pass
            return
        try:
            # rewrite absolute-form ("GET http://host/path") to origin-form ("GET /path")
            try:
                first, rest = buf.split(b"\r\n", 1)
                fp = first.split(b" ")
                if len(fp) >= 3 and b"://" in fp[1]:
                    after = fp[1].split(b"://", 1)[1]
                    path = b"/" + after.split(b"/", 1)[1] if b"/" in after else b"/"
                    buf = fp[0] + b" " + path + b" " + fp[2] + b"\r\n" + rest
            except Exception:
                pass
            up.sendall(buf)
            self._relay(c, up)
        finally:
            try:
                up.close()
            except Exception:
                pass

    def _relay(self, a, b):
        try:
            a.settimeout(None)
            b.settimeout(None)
            while True:
                r, _, _ = select.select([a, b], [], [], 120)
                if not r:
                    return
                for s in r:
                    data = s.recv(8192)
                    if not data:
                        return
                    (b if s is a else a).sendall(data)
        except Exception:
            return


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


# ---- Windows system-proxy registry helpers (no admin needed — HKCU) ----
_INTERNET_SETTINGS = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"


def _winproxy_get():
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _INTERNET_SETTINGS) as k:
        try:
            enable = winreg.QueryValueEx(k, "ProxyEnable")[0]
        except FileNotFoundError:
            enable = 0
        try:
            server = winreg.QueryValueEx(k, "ProxyServer")[0]
        except FileNotFoundError:
            server = ""
    return int(enable), str(server)


def _winproxy_set(enable, server):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _INTERNET_SETTINGS, 0, winreg.KEY_WRITE) as k:
        winreg.SetValueEx(k, "ProxyEnable", 0, winreg.REG_DWORD, 1 if enable else 0)
        # Always write ProxyServer (even ""), so a restore to "no proxy" fully clears the string
        # instead of leaving a stale 127.0.0.1:<port> behind.
        winreg.SetValueEx(k, "ProxyServer", 0, winreg.REG_SZ, server or "")
    _winproxy_refresh()


def _winproxy_refresh():
    import ctypes
    try:
        wininet = ctypes.windll.wininet
        wininet.InternetSetOptionW(0, 39, 0, 0)  # INTERNET_OPTION_SETTINGS_CHANGED
        wininet.InternetSetOptionW(0, 37, 0, 0)  # INTERNET_OPTION_REFRESH
    except Exception:
        pass


class ProxyFilter:
    """Owns the local proxy + the system-proxy switch for one focus session."""

    def __init__(self, data_dir=None):
        if data_dir is None:
            from task_manager.storage import storage
            data_dir = storage.data_dir
        self.data_dir = Path(data_dir)
        self.state_file = self.data_dir / "proxy_state.json"
        self.server = None
        self.thread = None
        self._saved = None

    def start(self, sites) -> bool:
        if sys.platform != "win32" or not sites:
            return False
        srv = _Server(("127.0.0.1", 0), _ProxyHandler)
        srv.blocked = list(sites)
        port = srv.server_address[1]
        self.server = srv
        self.thread = threading.Thread(target=srv.serve_forever, daemon=True)
        self.thread.start()

        # Save the user's current proxy BEFORE we change it (to memory AND disk for crash-recovery).
        try:
            self._saved = _winproxy_get()
        except Exception:
            self._saved = (0, "")
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(json.dumps({"enable": self._saved[0], "server": self._saved[1]}))
        except Exception:
            pass
        _winproxy_set(1, f"127.0.0.1:{port}")
        atexit.register(self.stop)   # restore on normal exit (signals can't be set off-main-thread)
        return True

    def stop(self):
        saved = self._saved
        if saved is None and self.state_file.exists():
            try:
                d = json.loads(self.state_file.read_text())
                saved = (int(d.get("enable", 0)), str(d.get("server", "")))
            except Exception:
                saved = (0, "")
        if saved is not None and sys.platform == "win32":
            try:
                _winproxy_set(saved[0], saved[1])
            except Exception:
                pass
        self._saved = None
        try:
            if self.state_file.exists():
                self.state_file.unlink()
        except Exception:
            pass
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass
            self.server = None

    @classmethod
    def rollback_if_stale(cls, data_dir=None):
        """Startup safety net: if a previous run died with the system proxy still pointed at our
        (now dead) local proxy, restore the saved setting so the user's connection isn't broken."""
        if sys.platform != "win32":
            return
        if data_dir is None:
            from task_manager.storage import storage
            data_dir = storage.data_dir
        sf = Path(data_dir) / "proxy_state.json"
        if not sf.exists():
            return
        try:
            d = json.loads(sf.read_text())
            _winproxy_set(int(d.get("enable", 0)), str(d.get("server", "")))
        except Exception:
            try:
                _winproxy_set(0, "")   # safest fallback: proxy off
            except Exception:
                pass
        try:
            sf.unlink()
        except Exception:
            pass
