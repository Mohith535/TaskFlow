from .gentle import GentleBlocker

class LinuxBlocker(GentleBlocker):
    """Linux blocker (placeholder - uses gentle mode)."""
    
    def get_status(self):
        status = super().get_status()
        status["platform"] = "linux"
        status["mode"] = "gentle"
        status["note"] = "Full blocking requires root permissions"
        return status