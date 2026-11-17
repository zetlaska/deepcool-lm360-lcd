"""IPC server and display state management."""

import json
import os
import socket
import threading
from pathlib import Path

from lm360.display import THEME_LIGHT, THEME_NAMES, render_solid_image, rgb_to_framebuffer


SOCKET_PATH = "/var/run/lm360/lm360.sock"
THEME_PATH = Path(os.environ.get("STATE_DIRECTORY", "/var/lib/lm360")) / "theme"
SOCKET_GROUP = "lm360"


class DisplayState:
    """Thread-safe display state."""

    def __init__(self, theme_path=THEME_PATH):
        self._mode = "monitor"
        self._framebuffer = None
        self._is_off = False
        self._theme_path = Path(theme_path)
        self._theme = _load_theme(self._theme_path)
        self._lock = threading.Lock()

    def set_monitor(self):
        """Switch to monitor mode."""
        with self._lock:
            self._mode = "monitor"
            self._framebuffer = None
            self._is_off = False

    def set_solid(self, framebuffer):
        """Switch to solid color mode."""
        with self._lock:
            self._mode = "solid"
            self._framebuffer = framebuffer
            self._is_off = False

    def set_off(self):
        """Turn screen off (black frame)."""
        with self._lock:
            self._is_off = True
            self._framebuffer = rgb_to_framebuffer(render_solid_image((0, 0, 0)))

    def set_on(self):
        """Turn screen on (resume previous mode)."""
        with self._lock:
            self._is_off = False
            if self._mode == "monitor":
                self._framebuffer = None

    def set_theme(self, theme):
        """Change monitor theme."""
        if theme not in THEME_NAMES:
            raise ValueError(f"Unknown theme: {theme}")
        with self._lock:
            _save_theme(self._theme_path, theme)
            self._theme = theme

    def get(self):
        """Get current display state (mode, framebuffer, theme, is_off)."""
        with self._lock:
            return self._mode, self._framebuffer, self._theme, self._is_off


class IPCServer:
    """Unix socket IPC server."""

    def __init__(self, device, display_state):
        self.device = device
        self.display_state = display_state
        self.running = False
        self.server_socket = None

    def start(self):
        """Start IPC server."""
        socket_dir = Path(SOCKET_PATH).parent
        socket_dir.mkdir(mode=0o750, parents=True, exist_ok=True)
        
        try:
            os.unlink(SOCKET_PATH)
        except FileNotFoundError:
            pass

        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.bind(SOCKET_PATH)
        
        # Set group-based permissions (0660) for lm360 group members
        try:
            import grp
            gid = grp.getgrnam(SOCKET_GROUP).gr_gid
            os.chown(SOCKET_PATH, -1, gid)
            os.chmod(SOCKET_PATH, 0o660)
        except (KeyError, PermissionError):
            # Fallback to root-only if group doesn't exist or no permission
            os.chmod(SOCKET_PATH, 0o600)
        
        self.server_socket.listen(4)
        self.running = True
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        """Accept and handle connections."""
        while self.running:
            try:
                connection, _ = self.server_socket.accept()
            except OSError:
                break
            connection.settimeout(5)
            self._handle(connection)

    def _handle(self, connection):
        """Handle single IPC request."""
        try:
            raw_request = _receive_all(connection, 64 * 1024)
            request = json.loads(raw_request.decode("utf-8"))
            action = request.get("action")

            if action == "brightness_up":
                self.device.brightness_up()
            elif action == "brightness_down":
                self.device.brightness_down()
            elif action == "monitor":
                self.display_state.set_monitor()
            elif action == "solid":
                color = _validate_color(request.get("color"))
                framebuffer = rgb_to_framebuffer(render_solid_image(color))
                self.display_state.set_solid(framebuffer)
            elif action == "theme":
                self.display_state.set_theme(request.get("theme"))
            elif action == "screen_off":
                self.display_state.set_off()
            elif action == "screen_on":
                self.display_state.set_on()
            elif action == "status":
                mode, _, theme, is_off = self.display_state.get()
                response = {"status": "ok", "running": True, "mode": mode, "theme": theme, "screen_off": is_off}
            else:
                raise ValueError(f"Unknown action: {action}")

            if action != "status":
                response = {"status": "ok"}
        except Exception as error:
            response = {"status": "error", "message": str(error)}

        try:
            connection.sendall(json.dumps(response).encode("utf-8"))
        except OSError:
            pass
        finally:
            connection.close()

    def stop(self):
        """Stop IPC server."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        try:
            os.unlink(SOCKET_PATH)
        except FileNotFoundError:
            pass


def send_ipc_command(command):
    """Send command to running service. Returns response dict or None if not running."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(5)
            client.connect(SOCKET_PATH)
            client.sendall(json.dumps(command).encode("utf-8"))
            client.shutdown(socket.SHUT_WR)
            response = _receive_all(client, 64 * 1024)
    except (FileNotFoundError, ConnectionRefusedError):
        return None
    except OSError as error:
        return {"status": "error", "message": str(error)}

    try:
        return json.loads(response.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return {"status": "error", "message": f"Invalid IPC response: {error}"}


def _receive_all(connection, limit):
    """Receive full message from connection."""
    data = bytearray()
    while True:
        chunk = connection.recv(4096)
        if not chunk:
            return bytes(data)
        data.extend(chunk)
        if len(data) > limit:
            raise ValueError(f"IPC message exceeds {limit} bytes")


def _load_theme(path):
    """Load saved theme preference."""
    try:
        theme = path.read_text(encoding="utf-8").strip()
    except OSError:
        return THEME_LIGHT
    return theme if theme in THEME_NAMES else THEME_LIGHT


def _save_theme(path, theme):
    """Save theme preference."""
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as output:
            output.write(f"{theme}\n")
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _validate_color(color):
    """Validate RGB color tuple."""
    if not isinstance(color, (list, tuple)) or len(color) != 3:
        raise ValueError("Color must contain three RGB values")
    if any(type(channel) is not int or not 0 <= channel <= 255 for channel in color):
        raise ValueError("RGB values must be 0-255")
    return tuple(color)
