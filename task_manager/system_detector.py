# task_manager/system_detector.py
import platform
import sys
import os


class SystemDetector:
    """Detect operating system and provide appropriate services."""
    
    @staticmethod
    def get_os():
        """Detect operating system."""
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "macos"
        elif system == "linux":
            return "linux"
        else:
            return "unknown"
    
    @staticmethod
    def is_admin():
        """Check if running with admin/root privileges."""
        try:
            os_type = SystemDetector.get_os()
            
            if os_type == "windows":
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            elif os_type in ["macos", "linux"]:
                import os
                return os.geteuid() == 0
            else:
                return False
        except:
            return False
    
    @staticmethod
    def get_distraction_blocker(force_gentle=False):
        """
        Get appropriate blocker for OS.
        
        Args:
            force_gentle: If True, always return GentleBlocker
        
        Returns:
            Appropriate blocker instance
        """
        os_type = SystemDetector.get_os()
        
        try:
            if os_type == "windows":
                if force_gentle or not SystemDetector.is_admin():
                    # Use absolute import
                    from task_manager.blockers.gentle import GentleBlocker
                    return GentleBlocker()
                else:
                    from task_manager.blockers.windows import WindowsBlocker
                    return WindowsBlocker()
            elif os_type == "macos":
                from task_manager.blockers.macos import MacOSBlocker
                return MacOSBlocker()
            elif os_type == "linux":
                from task_manager.blockers.linux import LinuxBlocker
                return LinuxBlocker()
            else:
                from task_manager.blockers.gentle import GentleBlocker
                return GentleBlocker()
        except ImportError as e:
            print(f"⚠️  Could not load platform blocker: {e}")
            # Try one more time with absolute import
            try:
                from task_manager.blockers.gentle import GentleBlocker
                return GentleBlocker()
            except:
                # Last resort: create a dummy blocker
                class DummyBlocker:
                    def block_websites(self, sites): print("Dummy: Would block", sites)
                    def unblock_websites(self): pass
                    def block_applications(self, apps): print("Dummy: Would block", apps)
                    def unblock_applications(self): pass
                    def start_focus(self, *args, **kwargs): print("Dummy focus started")
                    def end_focus(self): print("Dummy focus ended")
                    def get_status(self): return {"active": False}
                
                return DummyBlocker()
    
    @staticmethod
    def get_system_info():
        """Get detailed system information."""
        info = {
            "os": SystemDetector.get_os(),
            "admin": SystemDetector.is_admin(),
            "platform": platform.platform(),
            "python_version": sys.version.split()[0],
            "machine": platform.machine()
        }
        return info


# Quick test if run directly
if __name__ == "__main__":
    print("SystemDetector Test:")
    print(f"OS: {SystemDetector.get_os()}")
    print(f"Admin: {SystemDetector.is_admin()}")
    print(f"Info: {SystemDetector.get_system_info()}")