"""LCD rendering: PIL drawing and RGB565 encoding for 320x240 display."""

import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 320
HEIGHT = 240
FRAMEBUFFER_SIZE = WIDTH * HEIGHT * 2

_REGULAR_FONT_PATHS = (
    "/usr/share/fonts/TTF/DejaVuSansCondensed.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)
_BOLD_FONT_PATHS = (
    "/usr/share/fonts/TTF/DejaVuSansCondensed-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)

INK = (8, 10, 11)
PAPER = (244, 246, 246)
SIGNAL = (24, 209, 255)
MUTED = (92, 101, 105)
RULE = (199, 205, 207)

DARK_INK = (244, 246, 246)
DARK_PAPER = (8, 10, 11)
DARK_SIGNAL = (24, 209, 255)
DARK_MUTED = (154, 163, 166)
DARK_RULE = (53, 61, 64)

THEME_LIGHT = "light"
THEME_DARK = "dark"
THEME_NAMES = (THEME_LIGHT, THEME_DARK)
_THEME_PALETTES = {
    THEME_LIGHT: (INK, PAPER, SIGNAL, MUTED, RULE),
    THEME_DARK: (DARK_INK, DARK_PAPER, DARK_SIGNAL, DARK_MUTED, DARK_RULE),
}

WARN = (255, 92, 64)


def load_fonts():
    """Load DejaVu Sans fonts or fall back to defaults."""
    regular = _find_font(_REGULAR_FONT_PATHS)
    bold = _find_font(_BOLD_FONT_PATHS)
    if regular and bold:
        return {
            "temperature": ImageFont.truetype(bold, 44),
            "model": ImageFont.truetype(bold, 24),
            "data": ImageFont.truetype(bold, 16),
            "label": ImageFont.truetype(regular, 11),
            "micro": ImageFont.truetype(bold, 10),
        }

    default = ImageFont.load_default()
    return {key: default for key in ("temperature", "model", "data", "label", "micro")}


def render_monitor_image(snapshot, fonts=None, theme=THEME_LIGHT):
    """Render 320x240 monitor frame: CPU (temp/load/clock/RAM) and GPU (temp/load/clock/VRAM)."""
    fonts = fonts or load_fonts()
    try:
        ink, paper, signal, muted, rule = _THEME_PALETTES[theme]
    except KeyError as error:
        raise ValueError(f"Unknown theme: {theme}") from error

    image = Image.new("RGB", (WIDTH, HEIGHT), paper)
    draw = ImageDraw.Draw(image)
    left, right = 16, WIDTH - 16

    # 01 / CPU section
    y = 10
    _section(draw, fonts, y + 2, "01 / CPU", muted, signal)
    cpu_temp = _format_temperature(snapshot.cpu_temp)
    cpu_temp_x = right - _text_width(draw, cpu_temp, fonts["temperature"])
    cpu_model, cpu_font = _fit_text(draw, _format_cpu_model(snapshot.cpu_model), fonts["model"], cpu_temp_x - left - 12, minimum_size=15)
    draw.text((left, y + 16), cpu_model, fill=ink, font=cpu_font)
    _draw_right_text(draw, cpu_temp, right, y, ink, fonts["temperature"])
    _stat(draw, fonts, left, y + 46, "LOAD", _format_percent(snapshot.cpu_percent), ink, muted)
    draw.line((106, y + 46, 106, y + 62), fill=rule)
    _stat(draw, fonts, 118, y + 46, "CLOCK", _format_frequency(snapshot.cpu_freq), ink, muted)
    _memory_row(draw, fonts, y + 68, "RAM", getattr(snapshot, "ram_used", None), getattr(snapshot, "ram_total", None), ink, paper, signal, muted, rule)

    draw.line((left, 116, right, 116), fill=rule)

    # 02 / GPU section
    y = 126
    _section(draw, fonts, y + 2, "02 / GPU", muted, signal)
    gpu_temp_text = _format_temperature(snapshot.gpu_temp)
    gpu_temp_x = right - _text_width(draw, gpu_temp_text, fonts["temperature"])
    gpu_model, gpu_suffix = _split_gpu_model(snapshot.gpu_model)
    if gpu_suffix:
        gpu_model = f"{gpu_model} {gpu_suffix}"
    gpu_model, gpu_model_font = _fit_text(draw, gpu_model, fonts["model"], gpu_temp_x - left - 12, minimum_size=15)
    draw.text((left, y + 16), gpu_model, fill=ink, font=gpu_model_font)
    _draw_right_text(draw, gpu_temp_text, right, y, ink, fonts["temperature"])
    _stat(draw, fonts, left, y + 46, "LOAD", _format_percent(getattr(snapshot, "gpu_percent", None)), ink, muted)
    draw.line((106, y + 46, 106, y + 62), fill=rule)
    _stat(draw, fonts, 118, y + 46, "CLOCK", _format_frequency(getattr(snapshot, "gpu_clock", None)), ink, muted)
    _memory_row(draw, fonts, y + 68, "VRAM", getattr(snapshot, "vram_used", None), getattr(snapshot, "vram_total", None), ink, paper, signal, muted, rule)

    return image


def _memory_row(draw, fonts, y, label, used_mib, total_mib, ink, paper, signal, muted, rule):
    """Render 'LABEL used / total GiB   NN%' with usage bar below (values in MiB)."""
    left, right = 16, WIDTH - 16
    ok = (_valid_number(used_mib, 0, 1e9) and _valid_number(total_mib, 1, 1e9) and used_mib <= total_mib * 1.01)
    if ok:
        ratio = min(used_mib / total_mib, 1.0)
        amount = f"{used_mib / 1024:.1f} / {total_mib / 1024:.1f} GiB"
        percent = f"{ratio * 100:.0f}%"
    else:
        ratio, amount, percent = None, "N/A", ""
    draw.text((left, y + 4), label, fill=muted, font=fonts["micro"])
    value_x = left + max(_text_width(draw, "VRAM", fonts["micro"]), _text_width(draw, label, fonts["micro"])) + 8
    pct_w = _text_width(draw, percent, fonts["data"]) if percent else 0
    amount, amount_font = _fit_text(draw, amount, fonts["data"], right - value_x - pct_w - 8, minimum_size=12)
    draw.text((value_x, y), amount, fill=ink, font=amount_font)
    if percent:
        _draw_right_text(draw, percent, right, y, ink, fonts["data"])

    bar_top, bar_bottom = y + 22, y + 26
    draw.rectangle((left, bar_top, right, bar_bottom), fill=rule)
    if ratio:
        draw.rectangle((left, bar_top, left + max(1, round((right - left) * ratio)), bar_bottom), fill=WARN if ratio >= 0.9 else signal)
    for tick in (0.25, 0.5, 0.75):
        x = left + round((right - left) * tick)
        draw.line((x, bar_top, x, bar_bottom), fill=paper)


def _section(draw, fonts, y, label, muted, signal):
    draw.rectangle((16, y + 2, 18, y + 9), fill=signal)
    draw.text((24, y), label, fill=muted, font=fonts["micro"])


def _stat(draw, fonts, x, y, label, value, ink, muted):
    draw.text((x, y + 4), label, fill=muted, font=fonts["micro"])
    value_x = x + _text_width(draw, label, fonts["micro"]) + 8
    draw.text((value_x, y), value, fill=ink, font=fonts["data"])


def render_monitor_framebuffer(snapshot, fonts=None, theme=THEME_LIGHT):
    """Generate USB-ready RGB565 framebuffer."""
    return rgb_to_framebuffer(render_monitor_image(snapshot, fonts, theme))


def render_solid_image(color):
    """Render solid color image."""
    return Image.new("RGB", (WIDTH, HEIGHT), color=tuple(color))


def rgb_to_framebuffer(image):
    """Convert RGB image to 320x240 little-endian RGB565 data."""
    if image.mode != "RGB":
        image = image.convert("RGB")
    if image.size != (WIDTH, HEIGHT):
        image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)

    framebuffer = bytearray(FRAMEBUFFER_SIZE)
    pixels = image.tobytes()
    for pixel_offset in range(0, len(pixels), 3):
        red, green, blue = pixels[pixel_offset : pixel_offset + 3]
        rgb565 = ((red >> 3) << 11) | ((green >> 2) << 5) | (blue >> 3)
        offset = pixel_offset // 3 * 2
        framebuffer[offset] = rgb565 & 0xFF
        framebuffer[offset + 1] = rgb565 >> 8
    return bytes(framebuffer)


def framebuffer_to_rgb_image(framebuffer):
    """Decode device framebuffer to RGB image for preview."""
    if len(framebuffer) != FRAMEBUFFER_SIZE:
        raise ValueError(f"Framebuffer length error: {len(framebuffer)}, expected {FRAMEBUFFER_SIZE}")

    pixels = bytearray(WIDTH * HEIGHT * 3)
    for source_offset in range(0, FRAMEBUFFER_SIZE, 2):
        rgb565 = framebuffer[source_offset] | (framebuffer[source_offset + 1] << 8)
        red5 = (rgb565 >> 11) & 0x1F
        green6 = (rgb565 >> 5) & 0x3F
        blue5 = rgb565 & 0x1F
        target_offset = source_offset // 2 * 3
        pixels[target_offset] = (red5 << 3) | (red5 >> 2)
        pixels[target_offset + 1] = (green6 << 2) | (green6 >> 4)
        pixels[target_offset + 2] = (blue5 << 3) | (blue5 >> 2)
    return Image.frombytes("RGB", (WIDTH, HEIGHT), bytes(pixels))


def _find_font(paths):
    return next((path for path in paths if Path(path).is_file()), None)


def _fit_text(draw, text, font, max_width, minimum_size):
    """Shrink font to fit; truncate with ellipsis if below minimum size."""
    candidate = font
    if hasattr(font, "font_variant"):
        for size in range(font.size, minimum_size - 1, -1):
            candidate = font.font_variant(size=size)
            if _text_width(draw, text, candidate) <= max_width:
                return text, candidate
    elif _text_width(draw, text, font) <= max_width:
        return text, font

    marker = "..."
    if _text_width(draw, marker, candidate) > max_width:
        return "", candidate
    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        clipped = text[:middle].rstrip() + marker
        if _text_width(draw, clipped, candidate) <= max_width:
            low = middle
        else:
            high = middle - 1
    return text[:low].rstrip() + marker, candidate


def _format_cpu_model(model):
    model = re.sub(r"\s+", " ", (model or "Unknown").strip())
    model = re.sub(r"^\d+(?:st|nd|rd|th)\s+Gen\s+", "", model, flags=re.I)
    model = re.sub(r"^(?:AMD|Intel(?:\(R\))?)\s+", "", model, flags=re.I)
    model = re.sub(r"\bIntel(?:\(R\))?\s+", "", model, flags=re.I)
    model = re.sub(r"\((?:R|TM)\)", "", model, flags=re.I)
    model = re.sub(r"\bCPU\b\s*", "", model, flags=re.I)
    model = re.sub(r"\s+(?:w/|with)\s+Radeon.*$", "", model, flags=re.I)
    model = re.sub(r"\s+\d+-Cores?(?:\s+Processor)?$", "", model, flags=re.I)
    model = re.sub(r"\s+Processor$|\s+@\s+.*$", "", model, flags=re.I)
    model = re.sub(r"^Ryzen\s+Threadripper\s+", "TR ", model, flags=re.I)
    model = re.sub(r"^Ryzen\s+(\d)\s+", r"R\1 ", model)
    model = re.sub(r"^Core\s+", "", model)
    return re.sub(r"\s+", " ", model).strip() or "Unknown"


def _split_gpu_model(model):
    model = re.sub(r"\s+", " ", (model or "Unknown").strip())
    model = re.sub(r"^(?:NVIDIA\s+)?(?:GeForce\s+)?", "", model, flags=re.I)
    model = re.sub(r"(\d)(Ti|SUPER|XTX|XT|GRE)\b", r"\1 \2", model, flags=re.I)
    model = re.sub(r"\bTiSUPER\b", "Ti SUPER", model, flags=re.I)
    workstation = re.match(r"^(RTX(?:\s+PRO)?\s+[A-Z]?\d+)\s+(.+?)(?:\s+Workstation\s+Edition)?$", model, re.I)
    if workstation:
        return workstation.group(1), workstation.group(2)
    match = re.match(r"^(.*?\d)\s+(Ti(?:\s+SUPER)?|SUPER|XTX|XT|GRE)$", model, re.I)
    if not match:
        return model, ""
    return match.group(1), match.group(2)


def _text_width(draw, text, font):
    bounds = draw.textbbox((0, 0), text, font=font)
    return bounds[2] - bounds[0]


def _draw_right_text(draw, text, right, y, color, font):
    draw.text((right - _text_width(draw, text, font), y), text, fill=color, font=font)


def _format_temperature(value):
    return "N/A" if not _valid_number(value, -100, 200) else f"{value:.0f}°"


def _format_percent(value):
    return "N/A" if not _valid_number(value, 0, 100) else f"{value:.0f}%"


def _format_frequency(value):
    return "N/A" if not _valid_number(value, 0, 100) else f"{value:.2f} GHz"


def _valid_number(value, minimum, maximum):
    return (isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and minimum <= value <= maximum)
