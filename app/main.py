import click
import asyncio
from .security.identity import Identity
from .security.trust_store import TrustStore
from .discovery.mdns import MDNSDiscovery
from .transfer.server import TransferServer
from .transfer.client import TransferClient
from .device_registry import DeviceRegistry
from .grab_state import GrabState
from pathlib import Path

@click.group()
def main():
    pass

@main.command()
@click.option('--port', default=8080, help='Port to listen on')
def listen(port):
    """Start listening to receive files."""
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
def search():
    """Search for available devices on the network."""
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
@click.argument('file_path')
def grab(file_path):
    """Grab a file to send later (grab-and-release workflow)."""
    try:
        grab_state = GrabState()
        grab_state.grab(file_path)
        grabbed_path = Path(file_path).name
        click.echo(f"📎 Grabbed: {grabbed_path}")
        click.echo(f"   Use 'myshare send [ID]' to release to a device")
    except FileNotFoundError as e:
        click.echo(f"Error: {e}")

@main.command()
def release():
    """Release the currently grabbed file."""
    grab_state = GrabState()
    grabbed = grab_state.get_grabbed()
    if grabbed:
        grab_state.release()
        click.echo(f"Released: {Path(grabbed).name}")
    else:
        click.echo("No file grabbed")

@main.command()
def grabbed():
    """Show currently grabbed file."""
    grab_state = GrabState()
    click.echo(grab_state.show_grabbed())

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
            click.echo(f"Device {device_id} not found in registry. Run 'myshare search' first")
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
@click.argument('file_path', required=False)
def send(device_id, file_path):
    """Send a file to a device. If no file specified, uses grabbed file."""
    grab_state = GrabState()
    
    # If no file_path provided, try to use grabbed file
    if not file_path:
        file_path = grab_state.get_grabbed()
        if not file_path:
            click.echo("No file specified and no grabbed file. Use 'myshare grab <file>' first")
            return
        click.echo(f"📨 Sending grabbed file: {Path(file_path).name}")
    
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
            click.echo(f"Device {device_id} not found in registry. Run 'myshare search' first")
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
        # Auto-release grabbed file after successful send
        if grab_state.get_grabbed() == str(Path(file_path).absolute()):
            grab_state.release()
    except Exception as e:
        click.echo(f"Failed to send file: {e}")

if __name__ == '__main__':
    main()