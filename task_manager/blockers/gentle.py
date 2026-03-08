import subprocess
from .base import BaseBlocker
import threading
import time
import os
import sys

try:
    if sys.platform == "win32":
        import winsound
    else:
        winsound = None
except Exception:
    winsound = None


class GentleBlocker(BaseBlocker):
    """
    Enhanced gentle blocker with sound alerts and better reminders.
    Works without admin permissions on all platforms.
    """
    
    def __init__(self):
        super().__init__()
        self.motivational_messages = [
            "Stay focused! The finish line is closer than you think.",
            "Remember why you started this focus session.",
            "Every minute of focus brings you closer to your goal.",
            "You've got this! Avoid distractions for just a while longer.",
            "Think of how good you'll feel when this task is done.",
            "Distractions are temporary, accomplishment is permanent.",
            "One task at a time. You're doing great!",
            "The pain of discipline is less than the pain of regret."
        ]
    
    def _play_alert_sound(self):
        """Play a gentle alert sound."""
        try:
            if winsound:
                winsound.Beep(1000, 300)  # Higher pitch for focus start
        except:
            pass  # Silently fail if sound not available
    
    def _play_reminder_sound(self):
        """Play a reminder sound."""
        try:
            if winsound:
                winsound.Beep(800, 200)  # Lower pitch for reminders
        except:
            pass
    
    def block_websites(self, sites):
        """Gentle website blocking - reminders only, no system changes."""
        if not sites:
            return True
        
        print(f"\n🔔 GENTLE FOCUS MODE")
        print(f"   Avoiding: {', '.join(sites[:3])}")
        if len(sites) > 3:
            print(f"   ... and {len(sites) - 3} more")
        
        self._play_alert_sound()
        
        print("\n💡 Tips:")
        print("   1. Close browser tabs for these sites")
        print("   2. Consider using browser extensions to block them")
        print("   3. Turn off notifications for these sites")
        
        self.blocked_sites = sites
        self.is_gentle_mode = True  # Always gentle mode for this blocker
        return True
    
    def _enhanced_reminders(self, sites):
        """Send motivational reminders with sounds."""
        interval = 300  # 5 minutes = 300 seconds
        count = 0
        
        while not self.stop_reminders and count < 12:  # Max 12 reminders (1 hour)
            time.sleep(interval)
            
            if not self.stop_reminders and self.is_active:
                count += 1
                message = self.motivational_messages[count % len(self.motivational_messages)]
                
                print(f"\n⏰ FOCUS CHECK #{count}: {message}")
                print(f"   Still avoiding: {', '.join(sites[:2])}...")
                
                # Play reminder sound
                self._play_reminder_sound()
    
    def unblock_websites(self):
        """End gentle website blocking - just clear the list."""
        self.stop_gentle_reminders()
        
        if self.blocked_sites:
            print(f"\n✅ FOCUS SESSION COMPLETE!")
            print(f"   You can now visit: {', '.join(self.blocked_sites[:3])}")
            print(f"   Great job staying focused! 🎉")
        
        self.blocked_sites = []
        self.is_active = False
    
    def block_applications(self, apps):
        """Enhanced application blocking."""
        if apps:
            print(f"\n📱 APPLICATION FOCUS MODE")
            print(f"   Avoiding: {', '.join(apps[:3])}")
            
            self._play_alert_sound()
            
            print("\n💡 Tips:")
            print("   1. Close these apps completely")
            print("   2. Turn off notifications for these apps")
            print("   3. Use Windows Focus Assist (Win + A)")
        
        self.blocked_apps = apps
    
    def unblock_applications(self):
        """No action needed for gentle mode."""
        if self.blocked_apps:
            print(f"\n✅ You can now open: {', '.join(self.blocked_apps[:3])}")
            print(f"   Reward yourself for staying focused!")
        
        self.blocked_apps = []
    
    def get_status(self):
        """Get gentle blocker status."""
        base_status = super().get_status()
        base_status["mode"] = "gentle"
        base_status["description"] = "Enhanced reminder-based focus with sound alerts"
        return base_status