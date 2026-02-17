import hashlib
import pathlib
import time
import uuid
from aiohttp import FormData, ClientSession
from cryptography.hazmat.primitives import serialization
from .auth import Auth

class TransferClient:
    """Client for sending files over HTTPS."""

    def __init__(self, identity, trust_store):
        self.identity = identity
        self.trust_store = trust_store
        self.auth = Auth(identity, trust_store)

    async def get_pubkey(self, address, port):
        """Fetch public key from server."""
        url = f"https://{address}:{port}/pubkey"
        async with ClientSession() as session:
            async with session.get(url, ssl=False) as resp:
                if resp.status == 200:
                    pem = await resp.text()
                    pubkey = serialization.load_pem_public_key(pem.encode())
                    return pubkey
                else:
                    raise Exception("Failed to get pubkey")

    async def send_file(self, address, port, file_path, receiver_id):
        """Send a file to the server."""
        file_path = pathlib.Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_path} not found")

        with open(file_path, 'rb') as f:
            content = f.read()

        file_hash = hashlib.sha256(content).hexdigest()
        nonce = str(uuid.uuid4())
        timestamp = time.time()
        sender_id = self.identity.device_id

        signature = self.auth.create_auth_header(file_hash, nonce, timestamp, sender_id, receiver_id)

        # Serialize sender's public key
        pubkey_pem = self.identity.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        data = FormData()
        data.add_field('file', content, filename=file_path.name)
        data.add_field('filename', file_path.name)
        data.add_field('file_hash', file_hash)
        data.add_field('nonce', nonce)
        data.add_field('timestamp', str(timestamp))
        data.add_field('sender_id', sender_id)
        data.add_field('receiver_id', receiver_id)
        data.add_field('signature', signature)
        data.add_field('pubkey_pem', pubkey_pem)

        url = f"https://{address}:{port}/upload"
        async with ClientSession() as session:
            async with session.post(url, data=data, ssl=False) as resp:
                if resp.status == 200:
                    print("File sent successfully")
                else:
                    error = await resp.text()
                    print(f"Failed to send file: {error}")