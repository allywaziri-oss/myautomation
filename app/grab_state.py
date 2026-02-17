"""
Manages grabbed file state - storing the file path user wants to send.
Allows grab-and-release workflow where user grabs a file and releases it to a device.
"""

import json
from pathlib import Path
from datetime import datetime


class GrabState:
    def __init__(self):
        self.config_dir = Path.home() / '.myshare'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.grab_file = self.config_dir / 'grabbed_file.json'

    def grab(self, file_path):
        """Store grabbed file path."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        state = {
            'file_path': str(path.absolute()),
            'file_name': path.name,
            'grabbed_at': datetime.now().isoformat()
        }
        
        with open(self.grab_file, 'w') as f:
            json.dump(state, f)
    
    def get_grabbed(self):
        """Get currently grabbed file path."""
        if not self.grab_file.exists():
            return None
        
        try:
            with open(self.grab_file, 'r') as f:
                state = json.load(f)
            
            file_path = state.get('file_path')
            if file_path and Path(file_path).exists():
                return file_path
            else:
                # File no longer exists, clear state
                self.release()
                return None
        except Exception:
            return None
    
    def release(self):
        """Clear grabbed file."""
        if self.grab_file.exists():
            self.grab_file.unlink()
    
    def show_grabbed(self):
        """Display currently grabbed file."""
        grabbed = self.get_grabbed()
        if grabbed:
            return f"📎 Grabbed: {Path(grabbed).name}"
        else:
            return "No file grabbed yet"
