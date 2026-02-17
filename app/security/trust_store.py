import json
import pathlib
from cryptography.hazmat.primitives import serialization

class TrustStore:
    """Manage trusted devices."""

    def __init__(self):
        self.config_dir = pathlib.Path.home() / '.myshare'
        self.config_dir.mkdir(exist_ok=True)
        self.trust_file = self.config_dir / 'trust.json'
        self.trusted = {}
        if self.trust_file.exists():
            with open(self.trust_file) as f:
                data = json.load(f)
                for device_id, info in data.items():
                    pubkey_pem = info['pubkey']
                    pubkey = serialization.load_pem_public_key(pubkey_pem.encode())
                    self.trusted[device_id] = {
                        'device_name': info['device_name'],
                        'pubkey': pubkey
                    }

    def add_device(self, device_id, device_name, pubkey):
        self.trusted[device_id] = {
            'device_name': device_name,
            'pubkey': pubkey
        }
        self.save()

    def is_trusted(self, device_id):
        return device_id in self.trusted

    def get_pubkey(self, device_id):
        return self.trusted.get(device_id, {}).get('pubkey')

    def save(self):
        data = {}
        for device_id, info in self.trusted.items():
            pubkey_pem = info['pubkey'].public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode()
            data[device_id] = {
                'device_name': info['device_name'],
                'pubkey': pubkey_pem
            }
        with open(self.trust_file, 'w') as f:
            json.dump(data, f, indent=2)