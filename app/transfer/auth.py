import time
from cryptography.exceptions import InvalidSignature

class Auth:
    """Handle authentication for transfers."""

    def __init__(self, identity, trust_store):
        self.identity = identity
        self.trust_store = trust_store
        self.nonce_cache = set()
        self.timestamp_window = 300  # 5 minutes

    def create_auth_header(self, file_hash, nonce, timestamp, sender_id, receiver_id):
        """Create signature for the message."""
        message = f"{file_hash}:{nonce}:{timestamp}:{sender_id}:{receiver_id}".encode()
        signature = self.identity.private_key.sign(message)
        return signature.hex()

    def verify_auth(self, file_hash, nonce, timestamp, sender_id, receiver_id, signature_hex, pubkey):
        """Verify the authentication."""
        if nonce in self.nonce_cache:
            return False
        now = time.time()
        if abs(now - timestamp) > self.timestamp_window:
            return False
        message = f"{file_hash}:{nonce}:{timestamp}:{sender_id}:{receiver_id}".encode()
        signature = bytes.fromhex(signature_hex)
        try:
            pubkey.verify(signature, message)
            self.nonce_cache.add(nonce)
            return True
        except InvalidSignature:
            return False