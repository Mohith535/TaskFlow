from .base import BaseBlocker


class GentleBlocker(BaseBlocker):
    """
    Gentle blocker - uses reminders instead of enforcement.
    Works without admin permissions on all platforms.
    """
    
    def block_websites(self, sites):
        """Gentle website blocking (reminders only)."""
        if sites:
            print(f"\n🌐 Website Focus Mode Activated")
            print(f"   Avoiding: {', '.join(sites[:5])}")
            print(f"   {'...' if len(sites) > 5 else ''}")
            print("   Tip: Use browser extensions like 'StayFocusd' for actual blocking")
        
        # Log for analytics
        self.blocked_sites = sites
    
    def unblock_websites(self):
        """No action needed for gentle mode."""
        if self.blocked_sites:
            print(f"✅ You can now visit: {', '.join(self.blocked_sites[:3])}")
        self.blocked_sites = []
    
    def block_applications(self, apps):
        """Gentle application blocking (reminders only)."""
        if apps:
            print(f"\n📱 Application Focus Mode Activated")
            print(f"   Avoiding: {', '.join(apps[:5])}")
            print(f"   {'...' if len(apps) > 5 else ''}")
            print("   Tip: Close these apps manually for better focus")
        
        # Log for analytics
        self.blocked_apps = apps
    
    def unblock_applications(self):
        """No action needed for gentle mode."""
        if self.blocked_apps:
            print(f"✅ You can now open: {', '.join(self.blocked_apps[:3])}")
        self.blocked_apps = []
    
    def get_status(self):
        """Get gentle blocker status."""
        base_status = super().get_status()
        base_status["mode"] = "gentle"
        base_status["description"] = "Reminder-based focus assistance"
        return base_status