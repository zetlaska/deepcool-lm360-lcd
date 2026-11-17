"""Layout registry for extensible display modes."""

from lm360.display import render_monitor_framebuffer, render_solid_image, rgb_to_framebuffer


class Layout:
    """Base layout descriptor."""

    def __init__(self, name, description, render_fn):
        self.name = name
        self.description = description
        self.render_fn = render_fn

    def render(self, **kwargs):
        """Render framebuffer for this layout."""
        return self.render_fn(**kwargs)


_REGISTRY = {}


def register_layout(layout):
    """Register a layout."""
    _REGISTRY[layout.name] = layout


def get_layout(name):
    """Get layout by name."""
    if name not in _REGISTRY:
        raise ValueError(f"Unknown layout: {name}")
    return _REGISTRY[name]


def list_layouts():
    """List all registered layouts."""
    return list(_REGISTRY.values())


def _render_monitor(snapshot, fonts=None, theme="light"):
    """Render system monitor layout."""
    return render_monitor_framebuffer(snapshot, fonts, theme)


def _render_solid(color):
    """Render solid color layout."""
    return rgb_to_framebuffer(render_solid_image(color))


register_layout(Layout("monitor", "System monitor: CPU/GPU temp, load, clock, RAM/VRAM usage", _render_monitor))
register_layout(Layout("solid", "Solid color display", _render_solid))
