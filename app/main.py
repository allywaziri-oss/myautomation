import click
import asyncio
from .security.identity import Identity
from .security.trust_store import TrustStore
from .discovery.mdns import MDNSDiscovery
from .transfer.server import TransferServer
from .transfer.client import TransferClient

@click.group()
def main():
    pass

@main.command()
@click.option('--port', default=8080, help='Port to listen on')
def arm_receive(port):
    """Arm the device to receive files."""
    identity = Identity()
    trust_store = TrustStore()
    mdns = MDNSDiscovery(identity)
    mdns.advertise(port)
    server = TransferServer(identity, trust_store, port)
    try:
        asyncio.run(server.run())
    finally:
        mdns.stop()

@main.command()
def discover():
    """Discover available devices."""
    identity = Identity()
    mdns = MDNSDiscovery(identity)
    devices = asyncio.run(mdns.discover())
    for device in devices:
        print(f"{device['device_id']}: {device['device_name']} at {device['address']}:{device['port']}")

@main.command()
@click.argument('device_id')
def trust(device_id):
    """Trust a device by fetching its public key."""
    identity = Identity()
    trust_store = TrustStore()
    mdns = MDNSDiscovery(identity)
    devices = asyncio.run(mdns.discover())
    device = next((d for d in devices if d['device_id'] == device_id), None)
    if not device:
        click.echo("Device not found")
        return
    client = TransferClient(identity, trust_store)
    pubkey = asyncio.run(client.get_pubkey(device['address'], device['port']))
    device_name = device['device_name']
    trust_store.add_device(device_id, device_name, pubkey)
    click.echo(f"Trusted device {device_id}")

@main.command()
@click.argument('device_id')
@click.argument('file_path')
def send(device_id, file_path):
    """Send a file to a trusted device."""
    identity = Identity()
    trust_store = TrustStore()
    mdns = MDNSDiscovery(identity)
    devices = asyncio.run(mdns.discover())
    device = next((d for d in devices if d['device_id'] == device_id), None)
    if not device:
        click.echo("Device not found")
        return
    if not trust_store.is_trusted(device_id):
        click.echo("Device not trusted")
        return
    client = TransferClient(identity, trust_store)
    asyncio.run(client.send_file(device['address'], device['port'], file_path, device_id))

if __name__ == '__main__':
    main()