import click
import asyncio
from .security.identity import Identity
from .security.trust_store import TrustStore
from .discovery.mdns import MDNSDiscovery
from .transfer.server import TransferServer
from .transfer.client import TransferClient
from .device_registry import DeviceRegistry
from pathlib import Path

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
    config_dir = Path.home() / '.myshare'
    identity = Identity()
    registry = DeviceRegistry(config_dir)
    registry.clear()  # Clear old registry on each discover
    
    mdns = MDNSDiscovery(identity)
    devices = asyncio.run(mdns.discover())
    
    if not devices:
        click.echo("No devices found on the network")
        return
    
    click.echo("\nDiscovered Devices:")
    click.echo("-" * 60)
    for device in devices:
        short_id = registry.add_device(
            device['device_id'],
            device['device_name'],
            device['address'],
            device['port'],
            device['pubkey_fingerprint']
        )
        click.echo(f"[{short_id}] {device['device_name']} at {device['address']}:{device['port']}")
    click.echo("-" * 60)
    click.echo(f"\nUse 'myshare send [ID] <file>' to send to a device")

@main.command()
@click.argument('device_id')
def trust(device_id):
    """Trust a device by ID (4-digit or full UUID)."""
    config_dir = Path.home() / '.myshare'
    identity = Identity()
    trust_store = TrustStore()
    registry = DeviceRegistry(config_dir)
    
    # Check if it's a short ID (4-digit)
    device_info = None
    if len(device_id) == 4 and device_id.isdigit():
        device_info = registry.get_device_by_short_id(device_id)
        if device_info:
            actual_id = device_info['device_id']
        else:
            click.echo(f"Device {device_id} not found in registry. Run 'myshare discover' first")
            return
    else:
        # Full UUID provided
        actual_id = device_id
        device_info = registry.get_device_by_full_id(device_id)
    
    if not device_info:
        # Device not in registry, try to discover
        mdns = MDNSDiscovery(identity)
        devices = asyncio.run(mdns.discover())
        device_info = next((d for d in devices if d['device_id'] == actual_id), None)
        if not device_info:
            click.echo("Device not found")
            return
    
    client = TransferClient(identity, trust_store)
    try:
        pubkey = asyncio.run(client.get_pubkey(device_info['address'], device_info['port']))
        device_name = device_info['device_name']
        trust_store.add_device(actual_id, device_name, pubkey)
        click.echo(f"Trusted device {actual_id} ({device_name})")
    except Exception as e:
        click.echo(f"Failed to trust device: {e}")

@main.command()
@click.argument('device_id')
@click.argument('file_path')
def send(device_id, file_path):
    """Send a file to a device using short ID (0001) or full UUID."""
    config_dir = Path.home() / '.myshare'
    identity = Identity()
    trust_store = TrustStore()
    registry = DeviceRegistry(config_dir)
    
    # Check if it's a short ID (4-digit)
    device_info = None
    actual_device_id = device_id
    
    if len(device_id) == 4 and device_id.isdigit():
        device_info = registry.get_device_by_short_id(device_id)
        if device_info:
            actual_device_id = device_info['device_id']
        else:
            click.echo(f"Device {device_id} not found in registry. Run 'myshare discover' first")
            return
    else:
        # Full UUID provided
        device_info = registry.get_device_by_full_id(device_id)
        actual_device_id = device_id
    
    if not device_info:
        # Device not in registry, try to discover
        mdns = MDNSDiscovery(identity)
        devices = asyncio.run(mdns.discover())
        device_info = next((d for d in devices if d['device_id'] == actual_device_id), None)
        if not device_info:
            click.echo("Device not found")
            return
    
    client = TransferClient(identity, trust_store)
    try:
        asyncio.run(client.send_file(device_info['address'], device_info['port'], file_path, actual_device_id))
    except Exception as e:
        click.echo(f"Failed to send file: {e}")

if __name__ == '__main__':
    main()