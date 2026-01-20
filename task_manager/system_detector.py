import platform
import sys


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
    def get_distraction_blocker(force_gentle=False):
        """
        Get appropriate blocker for OS.
        
        Args:
            force_gentle: If True, always return GentleBlocker
        
        Returns:
            Appropriate blocker instance
        """
        if force_gentle:
            from .blockers.gentle import GentleBlocker
            return GentleBlocker()
        
        os_type = SystemDetector.get_os()
        
        try:
            if os_type == "windows":
                from .blockers.windows import WindowsBlocker
                return WindowsBlocker()
            elif os_type == "macos":
                from .blockers.macos import MacOSBlocker
                return MacOSBlocker()
            elif os_type == "linux":
                from .blockers.linux import LinuxBlocker
                return LinuxBlocker()
            else:
                from .blockers.gentle import GentleBlocker
                return GentleBlocker()
        except ImportError as e:
            print(f"⚠️  Could not load platform blocker: {e}")
            from .blockers.gentle import GentleBlocker
            return GentleBlocker()
    
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