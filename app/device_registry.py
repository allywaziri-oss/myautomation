"""Device registry for managing discovered devices with simple IDs."""
import json
from pathlib import Path


class DeviceRegistry:
    """Maintain a registry of discovered devices with simple 4-digit IDs."""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.registry_file = config_dir / "device_registry.json"
        self.registry = self.load()

    def load(self):
        """Load device registry from file."""
        if self.registry_file.exists():
            with open(self.registry_file, 'r') as f:
                return json.load(f)
        return {}

    def save(self):
        """Save device registry to file."""
        with open(self.registry_file, 'w') as f:
            json.dump(self.registry, f, indent=2)

    def add_device(self, device_id, device_name, address, port, pubkey_fingerprint):
        """Add a device to the registry, auto-assigning a 4-digit ID."""
        # Generate next available 4-digit ID
        existing_ids = [int(k) for k in self.registry.keys() if k.isdigit()]
        next_id = max(existing_ids) + 1 if existing_ids else 1
        short_id = f"{next_id:04d}"
        
        self.registry[short_id] = {
            'device_id': device_id,
            'device_name': device_name,
            'address': address,
            'port': port,
            'pubkey_fingerprint': pubkey_fingerprint
        }
        self.save()
        return short_id

    def get_device_by_short_id(self, short_id):
        """Get device info by short 4-digit ID."""
        if short_id in self.registry:
            return self.registry[short_id]
        return None

    def get_device_by_full_id(self, device_id):
        """Get device info by full device ID (UUID)."""
        for short_id, info in self.registry.items():
            if info['device_id'] == device_id:
                return {**info, 'short_id': short_id}
        return None

    def list_devices(self):
        """List all registered devices with short IDs."""
        return self.registry

    def clear(self):
        """Clear the registry."""
        self.registry = {}
        self.save()
