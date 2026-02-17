import asyncio
import pathlib
import re
import ssl
from aiohttp import web
from cryptography.hazmat.primitives import serialization
from .auth import Auth

class TransferServer:
    """HTTPS server for receiving files."""

    def __init__(self, identity, trust_store, port):
        self.identity = identity
        self.trust_store = trust_store
        self.port = port
        self.auth = Auth(identity, trust_store)
        self.incoming_dir = pathlib.Path.home() / 'Downloads' / 'MyShare' / 'Incoming'
        self.incoming_dir.mkdir(parents=True, exist_ok=True)

    async def run(self):
        app = web.Application()
        app.router.add_post('/upload', self.upload)
        app.router.add_get('/pubkey', self.get_pubkey)

        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(str(self.identity.cert_file), str(self.identity.key_file))

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port, ssl_context=ssl_context)
        await site.start()
        print(f"Server started on port {self.port}")
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            await runner.cleanup()

    async def get_pubkey(self, request):
        """Serve the public key."""
        pem = self.identity.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return web.Response(text=pem.decode())

    async def upload(self, request):
        """Handle file upload."""
        data = await request.post()
        file = data.get('file')
        filename = data.get('filename')
        file_hash = data.get('file_hash')
        nonce = data.get('nonce')
        timestamp = float(data.get('timestamp', 0))
        sender_id = data.get('sender_id')
        receiver_id = data.get('receiver_id')
        signature = data.get('signature')
        pubkey_pem = data.get('pubkey_pem')

        if not all([file, filename, file_hash, nonce, sender_id, receiver_id, signature]):
            return web.Response(status=400, text="Missing fields")

        # Try to get pubkey from trust store, or use the one from request
        pubkey = self.trust_store.get_pubkey(sender_id)
        if not pubkey:
            if pubkey_pem:
                try:
                    pubkey = serialization.load_pem_public_key(pubkey_pem)
                except Exception:
                    return web.Response(status=403, text="Invalid pubkey")
            else:
                return web.Response(status=403, text="Sender not trusted and no pubkey provided")

        if not self.auth.verify_auth(file_hash, nonce, timestamp, sender_id, receiver_id, signature, pubkey):
            return web.Response(status=403, text="Auth failed")

        # Save file
        safe_filename = self.safe_filename(filename)
        file_path = self.incoming_dir / safe_filename
        with open(file_path, 'wb') as f:
            f.write(file.file.read())

        return web.Response(text="OK")

    def safe_filename(self, filename):
        """Sanitize filename."""
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        return filename