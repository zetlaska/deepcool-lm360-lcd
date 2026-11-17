"""Command-line interface for lm360."""

import argparse
import sys
import time

from lm360.display import THEME_NAMES, load_fonts, render_monitor_image
from lm360.driver import LMDisplay
from lm360.layouts import list_layouts
from lm360.service import IPCServer, DisplayState, send_ipc_command
from lm360.system import SystemMonitor


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="DeepCool LM360 AIO LCD control", formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    start_parser = commands.add_parser("start", help="Start monitoring service")
    start_parser.add_argument("--interval", type=_positive_interval, default=2.0, help="Refresh interval in seconds (default: 2.0)")

    commands.add_parser("stop", help="Stop monitoring service (send SIGTERM)")
    commands.add_parser("status", help="Query service status")
    commands.add_parser("on", help="Turn screen on (resume previous mode)")
    commands.add_parser("off", help="Turn screen off (black frame)")

    brightness_parser = commands.add_parser("brightness", help="Adjust brightness")
    brightness_parser.add_argument("direction", choices=("up", "down"))

    theme_parser = commands.add_parser("theme", help="Switch monitor theme")
    theme_parser.add_argument("name", choices=THEME_NAMES)

    layout_parser = commands.add_parser("layout", help="Manage layouts")
    layout_commands = layout_parser.add_subparsers(dest="layout_command", required=True)
    layout_commands.add_parser("list", help="List available layouts")
    layout_set_parser = layout_commands.add_parser("set", help="Set active layout")
    layout_set_parser.add_argument("name", help="Layout name")

    preview_parser = commands.add_parser("preview", help="Generate preview image (headless)")
    preview_parser.add_argument("--output", default="preview.png", help="Output file")
    preview_parser.add_argument("--theme", choices=THEME_NAMES, default="light")

    args = parser.parse_args()

    try:
        if args.command == "start":
            return cmd_start(args.interval)
        elif args.command == "stop":
            return cmd_stop()
        elif args.command == "status":
            return cmd_status()
        elif args.command == "on":
            return cmd_screen_on()
        elif args.command == "off":
            return cmd_screen_off()
        elif args.command == "brightness":
            return cmd_brightness(args.direction)
        elif args.command == "theme":
            return cmd_theme(args.name)
        elif args.command == "layout":
            if args.layout_command == "list":
                return cmd_layout_list()
            elif args.layout_command == "set":
                return cmd_layout_set(args.name)
        elif args.command == "preview":
            return cmd_preview(args.output, args.theme)
    except RuntimeError as error:
        parser.exit(1, f"Error: {error}\n")


def cmd_start(interval):
    """Start monitoring service."""
    response = send_ipc_command({"action": "status"})
    if response and response.get("status") == "ok":
        print("Service is already running")
        return 1

    device = connect_device()
    try:
        run_monitor(device, interval)
    finally:
        device.disconnect()


def cmd_stop():
    """Stop service."""
    response = send_ipc_command({"action": "status"})
    if not response or response.get("status") != "ok":
        print("Service is not running")
        return 1
    print("Service is running. Send SIGTERM to stop it.")
    print("Use: sudo systemctl stop lm360")
    return 0


def cmd_status():
    """Query service status."""
    response = send_ipc_command({"action": "status"})
    if not response or response.get("status") != "ok":
        print("Service is not running")
        return 1
    print(f"Service running")
    print(f"  Mode: {response.get('mode', 'unknown')}")
    print(f"  Theme: {response.get('theme', 'unknown')}")
    print(f"  Screen: {'off' if response.get('screen_off') else 'on'}")
    return 0


def cmd_screen_on():
    """Turn screen on."""
    if not execute_remote({"action": "screen_on"}):
        return 1
    print("Screen turned on")
    return 0


def cmd_screen_off():
    """Turn screen off."""
    if not execute_remote({"action": "screen_off"}):
        return 1
    print("Screen turned off (black frame)")
    return 0


def cmd_brightness(direction):
    """Adjust brightness."""
    action = "brightness_up" if direction == "up" else "brightness_down"
    if execute_remote({"action": action}):
        print(f"Brightness {'increased' if direction == 'up' else 'decreased'}")
        return 0
    device = connect_device()
    try:
        if direction == "up":
            device.brightness_up()
        else:
            device.brightness_down()
    finally:
        device.disconnect()
    print(f"Brightness {'increased' if direction == 'up' else 'decreased'}")
    return 0


def cmd_theme(name):
    """Switch theme."""
    if not execute_remote({"action": "theme", "theme": name}):
        print("Service is not running")
        return 1
    print(f"Switched to {name} theme")
    return 0


def cmd_layout_list():
    """List available layouts."""
    print("Available layouts:")
    for layout in list_layouts():
        print(f"  {layout.name}: {layout.description}")
    return 0


def cmd_layout_set(name):
    """Set active layout."""
    if name == "monitor":
        if not execute_remote({"action": "monitor"}):
            print("Service is not running")
            return 1
        print(f"Switched to {name} layout")
        return 0
    print(f"Layout '{name}' is not yet implemented for live switching")
    return 1


def cmd_preview(output, theme):
    """Generate headless preview."""
    monitor = SystemMonitor()
    fonts = load_fonts()
    snapshot = monitor.sample()
    image = render_monitor_image(snapshot, fonts, theme)
    image.save(output)
    print(f"Preview saved to {output}")
    return 0


def run_monitor(device, interval):
    """Main monitoring loop."""
    device.initialize()
    time.sleep(0.5)

    display_state = DisplayState()
    ipc_server = IPCServer(device, display_state)
    ipc_server.start()
    monitor = SystemMonitor()
    fonts = load_fonts()
    frame_count = 0
    print(f"Monitoring started (interval: {interval}s, IPC: {ipc_server.server_socket.getsockname()})")

    try:
        while True:
            mode, framebuffer, theme, is_off = display_state.get()
            if is_off:
                status = "Screen off"
            elif mode == "monitor":
                snapshot = monitor.sample()
                framebuffer = render_monitor_image(snapshot, fonts, theme)
                from lm360.display import rgb_to_framebuffer
                framebuffer = rgb_to_framebuffer(framebuffer)
                status = _format_status(snapshot)
            else:
                status = "Solid color"

            if framebuffer:
                device.send_frame(framebuffer)
                frame_count += 1
            print(f"Frame {frame_count:4d} | {status:<60}", end="\r", flush=True)
            time.sleep(interval)
    except KeyboardInterrupt:
        print(f"\nMonitoring stopped, sent {frame_count} frames")
    finally:
        ipc_server.stop()


def execute_remote(command):
    """Execute command via IPC. Returns True on success."""
    response = send_ipc_command(command)
    if response is None:
        return False
    if response.get("status") != "ok":
        raise RuntimeError(response.get("message", "Unknown IPC error"))
    return True


def connect_device():
    """Connect to USB device."""
    device = LMDisplay()
    if device.connect():
        return device
    raise RuntimeError("Cannot connect to DeepCool LM device. Ensure USB device 3633:0026 is present and you have permissions.")


def _positive_interval(value):
    try:
        interval = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Interval must be numeric") from error
    if interval <= 0:
        raise argparse.ArgumentTypeError("Interval must be positive")
    return interval


def _format_status(snapshot):
    cpu_temp = "N/A" if snapshot.cpu_temp is None else f"{snapshot.cpu_temp:.1f}°C"
    cpu_usage = "N/A" if snapshot.cpu_percent is None else f"{snapshot.cpu_percent:.1f}%"
    gpu_temp = "N/A" if snapshot.gpu_temp is None else f"{snapshot.gpu_temp:.1f}°C"
    frequency = "N/A" if snapshot.cpu_freq is None else f"{snapshot.cpu_freq:.2f}GHz"
    return f"CPU {cpu_temp} ({cpu_usage}) | GPU {gpu_temp} | {frequency}"


if __name__ == "__main__":
    sys.exit(main())
