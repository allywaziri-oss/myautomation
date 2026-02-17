from cryptography.exceptions import InvalidSignature

class Handshake:
    """Handle cryptographic handshake operations."""

    def __init__(self, identity):
        self.identity = identity

    def sign_message(self, message: bytes) -> bytes:
        """Sign a message with the private key."""
        return self.identity.private_key.sign(message)

    def verify_message(self, message: bytes, signature: bytes, pubkey) -> bool:
        """Verify a message signature with the public key."""
        try:
            pubkey.verify(signature, message)
            return True
        except InvalidSignature:
            return False