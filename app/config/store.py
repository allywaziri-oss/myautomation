import json
import pathlib

class ConfigStore:
    """Store application configuration."""

    def __init__(self):
        self.config_dir = pathlib.Path.home() / '.myshare'
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / 'config.json'
        self.config = {}
        if self.config_file.exists():
            with open(self.config_file) as f:
                self.config = json.load(f)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()

    def save(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)