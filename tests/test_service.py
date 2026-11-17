"""Tests for IPC service."""

import json
import tempfile
import unittest
from pathlib import Path

from lm360.service import DisplayState, _load_theme, _save_theme, _validate_color


class ServiceTests(unittest.TestCase):
    def test_display_state_defaults_to_monitor(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = DisplayState(Path(tmpdir) / "theme")
            mode, framebuffer, theme, is_off = state.get()
            self.assertEqual(mode, "monitor")
            self.assertIsNone(framebuffer)
            self.assertEqual(theme, "light")
            self.assertFalse(is_off)

    def test_display_state_set_solid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = DisplayState(Path(tmpdir) / "theme")
            state.set_solid(b"test_framebuffer")
            mode, framebuffer, theme, is_off = state.get()
            self.assertEqual(mode, "solid")
            self.assertEqual(framebuffer, b"test_framebuffer")
            self.assertFalse(is_off)

    def test_display_state_set_off(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = DisplayState(Path(tmpdir) / "theme")
            state.set_off()
            mode, framebuffer, theme, is_off = state.get()
            self.assertTrue(is_off)
            self.assertIsNotNone(framebuffer)

    def test_display_state_set_on_resumes_monitor(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = DisplayState(Path(tmpdir) / "theme")
            state.set_off()
            state.set_on()
            mode, framebuffer, theme, is_off = state.get()
            self.assertEqual(mode, "monitor")
            self.assertIsNone(framebuffer)
            self.assertFalse(is_off)

    def test_display_state_set_theme(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            theme_path = Path(tmpdir) / "theme"
            state = DisplayState(theme_path)
            state.set_theme("dark")
            mode, framebuffer, theme, is_off = state.get()
            self.assertEqual(theme, "dark")
            self.assertEqual(_load_theme(theme_path), "dark")

    def test_display_state_invalid_theme_raises_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = DisplayState(Path(tmpdir) / "theme")
            with self.assertRaisesRegex(ValueError, "Unknown theme"):
                state.set_theme("invalid")

    def test_load_theme_missing_file_returns_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            theme = _load_theme(Path(tmpdir) / "nonexistent")
            self.assertEqual(theme, "light")

    def test_load_theme_invalid_content_returns_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "theme"
            path.write_text("invalid_theme\n")
            theme = _load_theme(path)
            self.assertEqual(theme, "light")

    def test_save_theme_persists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "theme"
            _save_theme(path, "dark")
            self.assertTrue(path.exists())
            self.assertEqual(path.read_text().strip(), "dark")

    def test_validate_color_valid(self):
        color = _validate_color([255, 128, 64])
        self.assertEqual(color, (255, 128, 64))

    def test_validate_color_invalid_length(self):
        with self.assertRaisesRegex(ValueError, "three RGB values"):
            _validate_color([255, 128])

    def test_validate_color_invalid_range(self):
        with self.assertRaisesRegex(ValueError, "0-255"):
            _validate_color([255, 128, 300])

    def test_validate_color_non_integer(self):
        with self.assertRaisesRegex(ValueError, "0-255"):
            _validate_color([255, 128.5, 64])


if __name__ == "__main__":
    unittest.main()
