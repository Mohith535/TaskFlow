from abc import ABC, abstractmethod
from datetime import datetime
import time
import threading


class BaseBlocker(ABC):
    """Base class for all distraction blockers."""
    
    def __init__(self):
        self.blocked_sites = []
        self.blocked_apps = []
        self.is_active = False
        self.start_time = None
        self.reminder_thread = None
        self.stop_reminders = False
    
    @abstractmethod
    def block_websites(self, sites):
        """Block specific websites."""
        pass
    
    @abstractmethod
    def unblock_websites(self):
        """Unblock all websites."""
        pass
    
    @abstractmethod
    def block_applications(self, apps):
        """Block specific applications."""
        pass
    
    @abstractmethod
    def unblock_applications(self):
        """Unblock all applications."""
        pass
    
    def start_gentle_reminders(self, sites, apps, interval_minutes=5):
        """Start gentle reminders (for non-admin mode)."""
        if sites or apps:
            self.stop_reminders = False
            self.reminder_thread = threading.Thread(
                target=self._send_reminders,
                args=(sites, apps, interval_minutes),
                daemon=True
            )
            self.reminder_thread.start()
    
    def _send_reminders(self, sites, apps, interval_minutes):
        """Send periodic gentle reminders."""
        reminder_count = 0
        max_reminders = 12  # Max reminders per session
        
        while (not self.stop_reminders and 
               reminder_count < max_reminders and 
               self.is_active):
            time.sleep(interval_minutes * 60)
            
            if not self.stop_reminders and self.is_active:
                reminder_count += 1
                
                # Create reminder message
                reminder_parts = []
                if sites:
                    site_list = ', '.join(sites[:3])
                    reminder_parts.append(f"sites: {site_list}")
                if apps:
                    app_list = ', '.join(apps[:3])
                    reminder_parts.append(f"apps: {app_list}")
                
                if reminder_parts:
                    print(f"\n⏰ Focus check: Avoid {', '.join(reminder_parts)}...")
    
    def stop_gentle_reminders(self):
        """Stop gentle reminders."""
        self.stop_reminders = True
        if self.reminder_thread and self.reminder_thread.is_alive():
            self.reminder_thread.join(timeout=2)
    
    def start_focus(self, sites=None, apps=None, gentle_mode=True):
        """Start focus session with blocking."""
        self.start_time = datetime.now()
        self.is_active = True
        
        if sites:
            self.blocked_sites = sites
            if gentle_mode:
                print(f"🔔 Gentle reminder: Try to avoid {', '.join(sites[:3])}")
            else:
                self.block_websites(sites)
        
        if apps:
            self.blocked_apps = apps
            if gentle_mode:
                print(f"📱 Gentle reminder: Try to avoid {', '.join(apps[:3])}")
            else:
                self.block_applications(apps)
        
        # Start gentle reminders if in gentle mode
        if gentle_mode and (sites or apps):
            self.start_gentle_reminders(sites, apps)
    
    def end_focus(self):
        """End focus session and restore everything."""
        self.stop_gentle_reminders()
        
        if not self.gentle_mode_active():
            self.unblock_websites()
            self.unblock_applications()
        
        self.is_active = False
        self.blocked_sites = []
        self.blocked_apps = []
        
        print("✅ Focus blocking ended. All restrictions removed.")
    
    def gentle_mode_active(self):
        """Check if we're in gentle mode (no actual blocking)."""
        # If we never actually blocked anything, we're in gentle mode
        return len(self.blocked_sites) > 0 or len(self.blocked_apps) > 0
    
    def get_status(self):
        """Get current blocking status."""
        return {
            "active": self.is_active,
            "since": self.start_time,
            "blocked_sites": self.blocked_sites,
            "blocked_apps": self.blocked_apps,
            "gentle_mode": self.gentle_mode_active(),
            "total_blocked": len(self.blocked_sites) + len(self.blocked_apps)
        }
    
    def __str__(self):
        """String representation."""
        status = self.get_status()
        if not status["active"]:
            return "Focus blocking: Inactive"
        
        mode = "Gentle reminders" if status["gentle_mode"] else "Full blocking"
        sites = f"{len(status['blocked_sites'])} sites" if status['blocked_sites'] else ""
        apps = f"{len(status['blocked_apps'])} apps" if status['blocked_apps'] else ""
        
        blocked = ", ".join(filter(None, [sites, apps]))
        return f"Focus blocking: {mode} on {blocked}"