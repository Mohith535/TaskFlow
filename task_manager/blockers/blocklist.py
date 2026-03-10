# task_manager/blockers/blocklist.py
import os
import json
from pathlib import Path

class BlocklistManager:
    """Manages the persistent list of websites to block."""
    
    def __init__(self):
        self.data_dir = Path.home() / ".taskflow"
        self.blocklist_file = self.data_dir / "blocklist.json"
        
        self.data_dir.mkdir(exist_ok=True)
        if not self.blocklist_file.exists():
            self.save_sites([])

    def load_sites(self):
        """Load blocked sites from storage."""
        try:
            with open(self.blocklist_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def save_sites(self, sites):
        """Save blocked sites to storage."""
        # Clean sites and remove empty
        sites = [site.strip() for site in sites if site.strip()]
        # Remove duplicates while preserving order
        unique_sites = list(dict.fromkeys(sites))
        
        with open(self.blocklist_file, 'w') as f:
            json.dump(unique_sites, f, indent=4)
        return unique_sites

    def add_sites(self, new_sites):
        """Add new sites to the blocklist."""
        current = self.load_sites()
        current.extend(new_sites)
        return self.save_sites(current)

    def remove_sites(self, indices):
        """Remove sites by their index (1-based)."""
        current = self.load_sites()
        # Sort indices in descending order to avoid shift issues during deletion
        indices = sorted([i for i in indices if 1 <= i <= len(current)], reverse=True)
        for i in indices:
            del current[i - 1]
        return self.save_sites(current)

blocklist_manager = BlocklistManager()
