"""USB driver for DeepCool LM360 (VID 0x3633 PID 0x0026)."""

import usb.core
import usb.util

from lm360.display import FRAMEBUFFER_SIZE


VENDOR_ID = 0x3633
PRODUCT_ID = 0x0026
EP_OUT = 0x01

FRAME_HEADER = bytes([0xAA, 0x08, 0x00, 0x00, 0x01, 0x00, 0x58, 0x02, 0x00, 0x2C, 0x01, 0xBC, 0x11])
BRIGHTNESS_UP = bytes([0xAA, 0x04, 0x00, 0x06, 0x03, 0x61, 0x00, 0xD2, 0x46])
BRIGHTNESS_DOWN = bytes([0xAA, 0x04, 0x00, 0x06, 0x03, 0x1D, 0x00, 0xE6, 0x0B])
INIT_QUERY = bytes([0xAA, 0x01, 0x00, 0x09, 0x29, 0x91])


class LMDisplay:
    """DeepCool LM360 USB interface."""

    def __init__(self):
        self.device = None
        self.interface = 0

    def connect(self):
        """Locate and claim USB device. Returns True on success."""
        self.device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
        if self.device is None:
            return False

        if self.device.is_kernel_driver_active(self.interface):
            try:
                self.device.detach_kernel_driver(self.interface)
            except Exception:
                pass
        try:
            # Re-sending SET_CONFIGURATION while endpoints are already active
            # fails on this host's xHCI controller with:
            #   "Trying to add endpoint 0x1 without dropping it."
            # After that, every later claim also fails until the USB device is
            # reset. If the kernel already selected a configuration, skip
            # set_configuration() and just claim the interface.
            try:
                active = self.device.get_active_configuration()
            except usb.core.USBError:
                active = None
            if active is None:
                self.device.set_configuration()
            usb.util.claim_interface(self.device, self.interface)
        except Exception:
            self.disconnect()
            return False
        return True

    def write(self, data):
        """Write data to USB endpoint."""
        try:
            written = self.device.write(EP_OUT, data, timeout=5000)
        except Exception as error:
            raise RuntimeError(f"USB write failed: {error}") from error
        if written != len(data):
            raise RuntimeError(f"Incomplete USB write: {written}/{len(data)} bytes")

    def send_frame(self, framebuffer):
        """Send 320x240 RGB565 framebuffer to display."""
        if len(framebuffer) != FRAMEBUFFER_SIZE:
            raise ValueError(f"Framebuffer length error: {len(framebuffer)}, expected {FRAMEBUFFER_SIZE}")
        self.write(FRAME_HEADER)
        self.write(framebuffer)

    def brightness_up(self):
        """Increase brightness (relative step)."""
        self.write(BRIGHTNESS_UP)

    def brightness_down(self):
        """Decrease brightness (relative step)."""
        self.write(BRIGHTNESS_DOWN)

    def initialize(self):
        """Send init/query command."""
        self.write(INIT_QUERY)

    def disconnect(self):
        """Release USB interface."""
        if not self.device:
            return
        try:
            usb.util.release_interface(self.device, self.interface)
            usb.util.dispose_resources(self.device)
        except Exception:
            pass
        finally:
            self.device = None
