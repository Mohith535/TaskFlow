from .gentle import GentleBlocker

class MacOSBlocker(GentleBlocker):
    """macOS blocker (placeholder - uses gentle mode)."""
    
    def get_status(self):
        status = super().get_status()
        status["platform"] = "macos"
        status["mode"] = "gentle"
        status["note"] = "Full blocking requires sudo permissions"
        return status