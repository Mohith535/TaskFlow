from .gentle import GentleBlocker
import subprocess
import os


class WindowsBlocker(GentleBlocker):
    """
    Windows-specific blocker with optional strict mode (requires admin).
    Falls back to gentle mode if not running as admin.
    """
    
    def __init__(self):
        super().__init__()
        self.is_admin = self._check_admin()
        self.hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
        self.hosts_backup = None
    
    def _check_admin(self):
        """Check if running as administrator."""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    
    def block_websites(self, sites):
        """Block websites on Windows (if admin, else gentle mode)."""
        if not self.is_admin:
            print("⚠️  Running in gentle mode. Run as Administrator for full website blocking.")
            return super().block_websites(sites)
        
        try:
            # Backup hosts file
            if os.path.exists(self.hosts_path):
                with open(self.hosts_path, 'r') as f:
                    self.hosts_backup = f.read()
            
            # Add blocked sites to hosts file
            with open(self.hosts_path, 'a') as f:
                f.write("\n# TaskFlow Focus Mode - Blocked Sites\n")
                for site in sites:
                    # Remove http:// and https://
                    clean_site = site.replace('http://', '').replace('https://', '').replace('www.', '')
                    f.write(f"127.0.0.1 {clean_site}\n")
                    f.write(f"127.0.0.1 www.{clean_site}\n")
            
            # Flush DNS cache
            subprocess.run(["ipconfig", "/flushdns"], capture_output=True)
            
            print(f"✅ Blocked {len(sites)} websites (Windows hosts file)")
            self.blocked_sites = sites
            return True
            
        except PermissionError:
            print("❌ Permission denied. Running in gentle mode.")
            return super().block_websites(sites)
        except Exception as e:
            print(f"❌ Could not block websites: {e}")
            return super().block_websites(sites)
    
    def unblock_websites(self):
        """Restore hosts file to original state."""
        if not self.is_admin or not self.hosts_backup:
            return super().unblock_websites()
        
        try:
            # Restore original hosts file
            with open(self.hosts_path, 'w') as f:
                f.write(self.hosts_backup)
            
            # Flush DNS cache
            subprocess.run(["ipconfig", "/flushdns"], capture_output=True)
            
            print("✅ Website blocking removed (hosts file restored)")
            self.blocked_sites = []
            self.hosts_backup = None
            return True
            
        except Exception as e:
            print(f"❌ Could not unblock websites: {e}")
            return super().unblock_websites()
    
    def block_applications(self, apps):
        """Block applications on Windows (if admin, else gentle)."""
        if not self.is_admin:
            print("⚠️  Running in gentle mode. Run as Administrator for full app blocking.")
            return super().block_applications(apps)
        
        try:
            blocked_count = 0
            for app in apps:
                # Try to kill running processes
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", f"{app}.exe"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 or "not found" not in result.stderr:
                    blocked_count += 1
            
            if blocked_count > 0:
                print(f"✅ Blocked {blocked_count} applications")
            else:
                print(f"ℹ️  No running instances found to block")
            
            self.blocked_apps = apps
            return True
            
        except Exception as e:
            print(f"❌ Could not block applications: {e}")
            return super().block_applications(apps)
    
    def unblock_applications(self):
        """Windows doesn't need special unblocking for apps."""
        super().unblock_applications()
    
    def get_status(self):
        """Get Windows blocker status."""
        status = super().get_status()
        status["platform"] = "windows"
        status["admin"] = self.is_admin
        status["mode"] = "strict" if self.is_admin else "gentle"
        return status