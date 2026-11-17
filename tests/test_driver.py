"""Tests for USB driver (mock-based, no hardware)."""

import unittest
from unittest.mock import MagicMock, patch

from lm360.driver import (
    BRIGHTNESS_DOWN,
    BRIGHTNESS_UP,
    FRAME_HEADER,
    INIT_QUERY,
    LMDisplay,
)


class DriverTests(unittest.TestCase):
    @patch("lm360.driver.usb.core.find")
    def test_connect_success(self, mock_find):
        mock_device = MagicMock()
        mock_device.is_kernel_driver_active.return_value = False
        mock_device.get_active_configuration.return_value = None
        mock_find.return_value = mock_device

        display = LMDisplay()
        result = display.connect()

        self.assertTrue(result)
        self.assertIsNotNone(display.device)
        mock_device.set_configuration.assert_called_once()

    @patch("lm360.driver.usb.core.find")
    def test_connect_skips_set_configuration_when_active(self, mock_find):
        # Re-sending SET_CONFIGURATION breaks some xHCI controllers
        # ("Trying to add endpoint 0x1 without dropping it").
        mock_device = MagicMock()
        mock_device.is_kernel_driver_active.return_value = False
        mock_device.get_active_configuration.return_value = MagicMock()
        mock_find.return_value = mock_device

        display = LMDisplay()
        result = display.connect()

        self.assertTrue(result)
        mock_device.set_configuration.assert_not_called()

    @patch("lm360.driver.usb.core.find")
    def test_connect_device_not_found(self, mock_find):
        mock_find.return_value = None

        display = LMDisplay()
        result = display.connect()

        self.assertFalse(result)
        self.assertIsNone(display.device)

    @patch("lm360.driver.usb.core.find")
    def test_connect_detaches_kernel_driver(self, mock_find):
        mock_device = MagicMock()
        mock_device.is_kernel_driver_active.return_value = True
        mock_find.return_value = mock_device

        display = LMDisplay()
        display.connect()

        mock_device.detach_kernel_driver.assert_called_once_with(0)

    @patch("lm360.driver.usb.core.find")
    def test_write_success(self, mock_find):
        mock_device = MagicMock()
        mock_device.is_kernel_driver_active.return_value = False
        mock_device.write.return_value = 10
        mock_find.return_value = mock_device

        display = LMDisplay()
        display.connect()
        display.write(b"1234567890")

        mock_device.write.assert_called_once()

    @patch("lm360.driver.usb.core.find")
    def test_write_incomplete_raises_error(self, mock_find):
        mock_device = MagicMock()
        mock_device.is_kernel_driver_active.return_value = False
        mock_device.write.return_value = 5
        mock_find.return_value = mock_device

        display = LMDisplay()
        display.connect()

        with self.assertRaisesRegex(RuntimeError, "Incomplete USB write"):
            display.write(b"1234567890")

    @patch("lm360.driver.usb.core.find")
    def test_send_frame_validates_size(self, mock_find):
        mock_device = MagicMock()
        mock_device.is_kernel_driver_active.return_value = False
        mock_find.return_value = mock_device

        display = LMDisplay()
        display.connect()

        with self.assertRaisesRegex(ValueError, "Framebuffer length error"):
            display.send_frame(b"short")

    @patch("lm360.driver.usb.core.find")
    def test_send_frame_writes_header_and_framebuffer(self, mock_find):
        mock_device = MagicMock()
        mock_device.is_kernel_driver_active.return_value = False
        mock_device.write.return_value = 13
        mock_find.return_value = mock_device

        display = LMDisplay()
        display.connect()

        framebuffer = b"\x00" * 153600
        mock_device.write.side_effect = [13, 153600]
        display.send_frame(framebuffer)

        self.assertEqual(mock_device.write.call_count, 2)
        first_call = mock_device.write.call_args_list[0][0]
        self.assertEqual(first_call[1], FRAME_HEADER)

    @patch("lm360.driver.usb.core.find")
    def test_brightness_up_sends_correct_command(self, mock_find):
        mock_device = MagicMock()
        mock_device.is_kernel_driver_active.return_value = False
        mock_device.write.return_value = len(BRIGHTNESS_UP)
        mock_find.return_value = mock_device

        display = LMDisplay()
        display.connect()
        display.brightness_up()

        mock_device.write.assert_called_once()
        self.assertEqual(mock_device.write.call_args[0][1], BRIGHTNESS_UP)

    @patch("lm360.driver.usb.core.find")
    def test_brightness_down_sends_correct_command(self, mock_find):
        mock_device = MagicMock()
        mock_device.is_kernel_driver_active.return_value = False
        mock_device.write.return_value = len(BRIGHTNESS_DOWN)
        mock_find.return_value = mock_device

        display = LMDisplay()
        display.connect()
        display.brightness_down()

        mock_device.write.assert_called_once()
        self.assertEqual(mock_device.write.call_args[0][1], BRIGHTNESS_DOWN)

    @patch("lm360.driver.usb.core.find")
    def test_initialize_sends_correct_command(self, mock_find):
        mock_device = MagicMock()
        mock_device.is_kernel_driver_active.return_value = False
        mock_device.write.return_value = len(INIT_QUERY)
        mock_find.return_value = mock_device

        display = LMDisplay()
        display.connect()
        display.initialize()

        mock_device.write.assert_called_once()
        self.assertEqual(mock_device.write.call_args[0][1], INIT_QUERY)

    @patch("lm360.driver.usb.core.find")
    def test_disconnect_releases_interface(self, mock_find):
        mock_device = MagicMock()
        mock_device.is_kernel_driver_active.return_value = False
        mock_find.return_value = mock_device

        display = LMDisplay()
        display.connect()
        display.disconnect()

        self.assertIsNone(display.device)


if __name__ == "__main__":
    unittest.main()
