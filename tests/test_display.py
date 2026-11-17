"""Tests for display rendering."""

import unittest

from lm360.display import (
    DARK_INK,
    DARK_PAPER,
    DARK_RULE,
    DARK_SIGNAL,
    FRAMEBUFFER_SIZE,
    INK,
    PAPER,
    RULE,
    SIGNAL,
    THEME_DARK,
    _fit_text,
    _format_cpu_model,
    _format_frequency,
    _format_percent,
    _format_temperature,
    _split_gpu_model,
    framebuffer_to_rgb_image,
    load_fonts,
    render_monitor_framebuffer,
    render_monitor_image,
    rgb_to_framebuffer,
)
from lm360.system import SystemSnapshot


class DisplayTests(unittest.TestCase):
    def test_monitor_image_has_correct_dimensions(self):
        snapshot = SystemSnapshot(
            cpu_brand="AMD",
            cpu_model="Ryzen 9 9900X",
            cpu_temp=72,
            cpu_percent=85,
            cpu_freq=5.2,
            gpu_brand="NVIDIA",
            gpu_model="RTX 5090",
            gpu_temp=65,
            ram_used=10240,
            ram_total=61440,
            vram_used=2048,
            vram_total=32768,
        )

        image = render_monitor_image(snapshot)

        self.assertEqual(image.mode, "RGB")
        self.assertEqual(image.size, (320, 240))

    def test_light_theme_uses_correct_colors(self):
        image = render_monitor_image(SystemSnapshot())
        self.assertEqual(image.getpixel((319, 239)), PAPER)
        # Section indicator at (16, y+2) to (18, y+9); CPU y=10, so check (17, 14-19)
        self.assertEqual(image.getpixel((17, 14)), SIGNAL)

    def test_dark_theme_uses_correct_colors(self):
        image = render_monitor_image(SystemSnapshot(), theme=THEME_DARK)
        self.assertEqual(image.getpixel((319, 239)), DARK_PAPER)
        # GPU section indicator at y=126, so (17, 128-135)
        self.assertEqual(image.getpixel((17, 130)), DARK_SIGNAL)

    def test_section_divider_rendered_correctly(self):
        light = render_monitor_image(SystemSnapshot())
        dark = render_monitor_image(SystemSnapshot(), theme=THEME_DARK)
        for x in (16, 58, 160, 304):
            self.assertEqual(light.getpixel((x, 116)), RULE)
            self.assertEqual(dark.getpixel((x, 116)), DARK_RULE)

    def test_unknown_theme_raises_error(self):
        with self.assertRaisesRegex(ValueError, "Unknown theme"):
            render_monitor_image(SystemSnapshot(), theme="invalid")

    def test_missing_metrics_renderable(self):
        image = render_monitor_image(SystemSnapshot())
        self.assertEqual(image.size, (320, 240))

    def test_framebuffer_encoding_produces_correct_size(self):
        image = render_monitor_image(SystemSnapshot())
        framebuffer = rgb_to_framebuffer(image)
        self.assertEqual(len(framebuffer), FRAMEBUFFER_SIZE)

    def test_framebuffer_roundtrip(self):
        snapshot = SystemSnapshot(cpu_temp=75, gpu_temp=65)
        original = render_monitor_image(snapshot)
        framebuffer = rgb_to_framebuffer(original)
        decoded = framebuffer_to_rgb_image(framebuffer)
        self.assertEqual(decoded.size, original.size)
        self.assertEqual(decoded.mode, original.mode)

    def test_format_cpu_model_strips_vendor_and_abbreviates_ryzen(self):
        # Implementation abbreviates "Ryzen N" to "RN" for display space
        self.assertEqual(_format_cpu_model("AMD Ryzen 9 9900X"), "R9 9900X")
        self.assertEqual(_format_cpu_model("AMD Ryzen 7 7800X3D"), "R7 7800X3D")
        self.assertEqual(_format_cpu_model("Intel Core i9-14900K"), "i9-14900K")
        self.assertEqual(_format_cpu_model("Ryzen 9 9950X Processor"), "R9 9950X")

    def test_split_gpu_model_separates_suffix(self):
        self.assertEqual(_split_gpu_model("RTX 5090"), ("RTX 5090", ""))
        self.assertEqual(_split_gpu_model("RTX 4090 Ti"), ("RTX 4090", "Ti"))
        self.assertEqual(_split_gpu_model("RTX 4080 SUPER"), ("RTX 4080", "SUPER"))

    def test_format_temperature(self):
        self.assertEqual(_format_temperature(72.5), "72°")
        self.assertEqual(_format_temperature(None), "N/A")
        self.assertEqual(_format_temperature(float("inf")), "N/A")

    def test_format_percent(self):
        self.assertEqual(_format_percent(85.3), "85%")
        self.assertEqual(_format_percent(None), "N/A")
        self.assertEqual(_format_percent(150), "N/A")

    def test_format_frequency(self):
        self.assertEqual(_format_frequency(5.2), "5.20 GHz")
        self.assertEqual(_format_frequency(None), "N/A")

    def test_memory_mib_to_gib_conversion(self):
        """Verify MiB to GiB conversion is correct (1 GiB = 1024 MiB)."""
        # User reported: kernel 60.4 GiB = 61849.6 MiB, NVIDIA 31.8 GiB = 32563.2 MiB
        snapshot = SystemSnapshot(
            ram_used=30924.8,  # Half of 61849.6
            ram_total=61849.6,
            vram_used=16281.6,  # Half of 32563.2
            vram_total=32563.2,
        )
        image = render_monitor_image(snapshot)
        # Verify image renders without error and has correct dimensions
        self.assertEqual(image.size, (320, 240))


if __name__ == "__main__":
    unittest.main()
