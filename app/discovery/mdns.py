import asyncio
import socket
from zeroconf import Zeroconf, ServiceInfo
from zeroconf.asyncio import AsyncZeroconf, AsyncServiceBrowser
from zeroconf._exceptions import NonUniqueNameException

class MDNSDiscovery:
    """Handle mDNS discovery and advertising."""

    def __init__(self, identity):
        self.identity = identity
        self.zeroconf = None
        self.service_type = "_myshare._tcp.local."
        self.service_name = f"{self.identity.device_id}.{self.service_type}"

    def advertise(self, port):
        """Advertise the service."""
        self.zeroconf = Zeroconf()
        device_name = socket.gethostname()
        txt = {
            'device_id': self.identity.device_id,
            'device_name': device_name,
            'port': str(port),
            'pubkey_fingerprint': self.identity.get_pubkey_fingerprint()
        }
        info = ServiceInfo(
            self.service_type,
            self.service_name,
            addresses=[socket.inet_aton(self.get_local_ip())],
            port=port,
            properties=txt
        )
        try:
            self.zeroconf.register_service(info)
        except NonUniqueNameException:
            # Service already registered, unregister and re-register
            try:
                self.zeroconf.unregister_service(info)
                self.zeroconf.register_service(info)
            except Exception as e:
                print(f"Warning: Could not re-register service: {e}")
                # Continue anyway - the old service should timeout

    def stop(self):
        """Stop advertising."""
        if self.zeroconf:
            self.zeroconf.unregister_all_services()
            self.zeroconf.close()

    async def discover(self):
        """Discover available services."""
        from zeroconf.asyncio import AsyncServiceInfo
        aiozc = AsyncZeroconf()
        services = []
        found_names = []

        class Listener:
            def add_service(self, zc, type_, name):
                if name not in found_names:
                    found_names.append(name)

            def update_service(self, zc, type_, name):
                pass

            def remove_service(self, zc, type_, name):
                pass

        listener = Listener()
        browser = AsyncServiceBrowser(aiozc.zeroconf, self.service_type, listener)
        await asyncio.sleep(5)  # Wait for discovery
        await browser.async_cancel()

        for name in found_names:
            info = AsyncServiceInfo(self.service_type, name)
            await info.async_request(aiozc.zeroconf, 3000)
            if info.addresses:
                txt = {k.decode(): v.decode() for k, v in info.properties.items()}
                services.append({
                    'device_id': txt.get('device_id'),
                    'device_name': txt.get('device_name'),
                    'address': socket.inet_ntoa(info.addresses[0]),
                    'port': info.port,
                    'pubkey_fingerprint': txt.get('pubkey_fingerprint')
                })

        await aiozc.async_close()
        return services

    def get_local_ip(self):
        """Get local IP address."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        return ip