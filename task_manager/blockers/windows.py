# task_manager/blockers/windows.py
from .base import BaseBlocker
import subprocess
import os
import sys


class WindowsBlocker(BaseBlocker):
    """
    Windows-specific blocker with actual system blocking.
    Requires admin privileges for strict mode.
    """
    
    def __init__(self):
        super().__init__()
        
        self.is_admin = self._check_admin()
        self.hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
        self.hosts_backup = None
        self.gentle_mode = not self.is_admin
    
    def _check_admin(self):
        """Check if running as administrator."""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    
    def block_websites(self, sites):
        """Actually block websites on Windows using hosts file."""
        if not sites:
            return True
        
        # If not admin, fall back to gentle mode
        if not self.is_admin:
            print("\n⚠️  WINDOWS GENTLE MODE (Admin required for strict blocking)")
            print("   Showing reminders instead of actual blocking...")
            self.is_gentle_mode = True
            return self._gentle_block_websites(sites)
        
        print(f"\n🚫 WINDOWS STRICT BLOCKING ACTIVATED")
        print(f"   Blocking {len(sites)} websites...")
        
        # ADD CONFIRMATION FOR STRICT MODE
        from task_manager.commands import confirm_action
        if not confirm_action("\n⚠️ WARNING: Strict mode modifies system files (hosts)."
                              "\nAre you sure you want to block these sites?"):
            print("   Strict blocking cancelled. Proceeding with gentle reminders.")
            self.is_gentle_mode = True
            return self._gentle_block_websites(sites)
        
        try:
            # Read current hosts file
            if os.path.exists(self.hosts_path):
                with open(self.hosts_path, 'r') as f:
                    self.hosts_backup = f.read()
            else:
                self.hosts_backup = ""
            
            # Prepare new entries
            new_entries = ["\n# TaskFlow Focus Mode - Blocked Sites"]
            
            for site in sites:
                # Clean the site name
                clean_site = site.replace('http://', '').replace('https://', '').replace('www.', '')
                
                # Check if already in hosts file
                if clean_site in self.hosts_backup:
                    print(f"   ℹ️  {clean_site} already blocked")
                    continue
                # Add IPv4 blocking entries
                new_entries.append(f"127.0.0.1 {clean_site}")
                new_entries.append(f"127.0.0.1 www.{clean_site}")
                
                # Add IPv6 blocking entries (forces modern browsers to fail faster)
                new_entries.append(f"::1 {clean_site}")
                new_entries.append(f"::1 www.{clean_site}")
                
                # Special case for youtube to handle aggressive browser routing
                if "youtube" in clean_site:
                    new_entries.append(f"127.0.0.1 m.{clean_site}")
                    new_entries.append(f"127.0.0.1 ytimg.com")
                    new_entries.append(f"::1 m.{clean_site}")
                    new_entries.append(f"::1 ytimg.com")
                
                print(f"   ✅ Blocking: {clean_site}")
            
            if len(new_entries) > 1:  # More than just the header
                # Add to hosts file
                with open(self.hosts_path, 'a') as f:
                    f.write("\n".join(new_entries) + "\n")
                
            # Flush DNS cache
            print("   🔄 Flushing DNS cache...")
            subprocess.run(
                ["ipconfig", "/flushdns"],
                capture_output=True,
                text=True,
                shell=True
            )
            
            # AGGRESSIVE BROWSER KILL FEATURE
            print(f"\n🎯 Strict blocking active for {len(sites)} websites")
            if confirm_action("\n⚠️ Browsers keep existing connections alive bypassing blocks."
                              "\nForce close all browsers now to ensure blocks apply? (y/N)"):
                browsers = ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"]
                killed = 0
                print("   🧹 Closing browsers...")
                for browser in browsers:
                    result = subprocess.run(
                        ["taskkill", "/F", "/IM", browser],
                        capture_output=True,
                        text=True,
                        shell=True
                    )
                    if result.returncode == 0:
                        killed += 1
                if killed > 0:
                    print("   ✅ Browsers closed successfully.")
                else:
                    print("   ℹ️ No active browsers found to close.")
            else:
                print("   ⚠️ Restart your browser MANUALLY for changes to take effect.")
            
            self.blocked_sites = sites
            self.is_active = True
            self.is_gentle_mode = False  # Strict mode active
            
            return True
            
        except PermissionError:
            print("❌ Permission denied! Could not write to hosts file.")
            self.is_gentle_mode = True
            return self._gentle_block_websites(sites)
    
    def _gentle_block_websites(self, sites):
        """Fallback gentle blocking (when not admin)."""
        print(f"\n🔔 WINDOWS GENTLE MODE")
        print(f"   Reminders for: {', '.join(sites[:3])}")
        print("\n💡 To enable strict blocking:")
        print("   1. Close this terminal")
        print("   2. Right-click Command Prompt")
        print("   3. Select 'Run as administrator'")
        print("   4. Run the focus command again")
        
        self.blocked_sites = sites
        return True
    
    def unblock_websites(self):
        """Remove our blocking entries from hosts file."""
        import shutil
        print("🔄 Removing blocking for all websites...")
        
        if not self.is_admin:
            print("⚠️  Not running as admin - limited cleanup capability")
            # We continue anyway to see if we can read and clean it if possible
        
        try:
            if not os.path.exists(self.hosts_path):
                return True
                
            # Read file
            with open(self.hosts_path, 'r') as f:
                lines = f.readlines()
            
            # Find our block
            start_index = -1
            for i, line in enumerate(lines):
                if "# TaskFlow Focus Mode - Blocked Sites" in line:
                    start_index = i
                    break
            
            if start_index == -1:
                print("   No TaskFlow blocks found")
                self.blocked_sites = []
                self.is_active = False
                return True
            
            # Count how many lines to remove
            block_lines = 1  # The header
            i = start_index + 1
            while i < len(lines):
                line = lines[i].strip()
                if line == "" or line.startswith("#"):
                    break
                if "127.0.0.1" in line or "::1" in line:
                    block_lines += 1
                i += 1
            
            # Remove the block
            new_lines = lines[:start_index] + lines[start_index + block_lines:]
            
            # Write backup first! (Safety)
            backup_path = self.hosts_path + ".taskflow_backup"
            try:
                with open(backup_path, 'w') as f:
                    f.writelines(lines)
            except PermissionError:
                pass # Can't write backup, probably in protected dir, just rely on try/except for hosts
            
            # Write cleaned file
            with open(self.hosts_path, 'w') as f:
                f.writelines(new_lines)
            
            # Flush DNS
            subprocess.run(["ipconfig", "/flushdns"], capture_output=True, text=True, shell=True)
            
            print(f"✅ Removed {block_lines} blocking lines")
            self.blocked_sites = []
            self.is_active = False
            
            print("\n💡 IMPORTANT: Restart browser completely!")
            print("   Close ALL browser windows and reopen")
            
            return True
            
        except PermissionError:
            print("❌ Permission denied! Run as Administrator.")
            return False
        except Exception as e:
            print(f"❌ Unblocking failed: {e}")
            # Try to restore from backup if something went wrong
            backup_path = self.hosts_path + ".taskflow_backup"
            if os.path.exists(backup_path):
                try:
                    shutil.copy2(backup_path, self.hosts_path)
                    print("✅ Restored from backup")
                except Exception:
                    pass
            return False
    
    def block_applications(self, apps):
        """Block applications on Windows."""
        if not apps:
            return True
        
        print(f"\n📱 Application blocking: {len(apps)} apps")
        
        if not self.is_admin:
            print("⚠️  Gentle mode (Admin required for strict app blocking)")
            print(f"   Please close: {', '.join(apps[:3])}")
            self.blocked_apps = apps
            return True
        
        blocked_count = 0
        for app in apps:
            try:
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", f"{app}.exe"],
                    capture_output=True,
                    text=True,
                    shell=True
                )
                
                if result.returncode == 0:
                    print(f"   ✅ Stopped: {app}")
                    blocked_count += 1
                elif "not found" in result.stderr.lower():
                    print(f"   ℹ️  {app} not running")
            
            except Exception as e:
                print(f"   ⚠️  Could not block {app}: {e}")
        
        self.blocked_apps = apps
        
        if blocked_count > 0:
            print(f"✅ Blocked {blocked_count} applications")
        else:
            print("ℹ️  No applications were running")
        
        return True
    
    def unblock_applications(self):
        """Applications can be restarted manually."""
        if self.blocked_apps:
            print(f"✅ You can now open: {', '.join(self.blocked_apps[:3])}")
            if len(self.blocked_apps) > 3:
                print(f"   ... and {len(self.blocked_apps) - 3} more")
        
        self.blocked_apps = []
        return True
    
    def get_status(self):
        status = super().get_status()
        status.update({
            "platform": "windows",
            "admin": self.is_admin,
            "mode": "strict" if self.is_admin and not self.gentle_mode else "gentle",
            "hosts_file": self.hosts_path
        })
        return status