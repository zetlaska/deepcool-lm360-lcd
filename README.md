# lm360 - DeepCool LM360 AIO LCD Control for Linux

A clean, maintainable Linux driver for the DeepCool LM360 AIO cooler LCD display. Features system monitoring with CPU/GPU metrics, RAM/VRAM usage, extensible layouts, and full CLI control.

![lm360 preview](preview.png)

## Features

- **System Monitor Layout**: CPU/GPU temperature, load, clock speed, RAM/VRAM usage with progress bars
- **Brightness Control**: Relative brightness adjustment (up/down steps)
- **Screen Control**: Deterministic on/off via black frame rendering
- **Theme Support**: Light and dark themes with live switching
- **Extensible Layouts**: Registry-based layout system for future additions
- **IPC Communication**: Unix socket for conflict-free CLI usage
- **Systemd Integration**: Background service with automatic restart
- **Hardware Support**: AMD Ryzen (k10temp), Intel Core (coretemp), NVIDIA GPUs (nvidia-smi)

## Hardware Compatibility

| Model | USB VID:PID | Status |
|-------|-------------|--------|
| DeepCool LM360 | 3633:0026 | **Tested** (Ryzen 9900X + RTX 5090) |
| DeepCool LM240 | 3633:0026 | Untested (likely compatible) |
| DeepCool LM280 | 3633:0026 | Untested (likely compatible) |

**Note**: Only the LM360 has been hardware-verified. Other LM-series models sharing the same USB VID:PID should work but have not been tested.

## Requirements

### Runtime Dependencies

- Python 3.10+
- PyUSB 1.2+
- psutil 5.9+
- Pillow 9.0+
- lm_sensors
- DejaVu Sans fonts
- pciutils (lspci)
- usbutils (lsusb)

### Optional Dependencies

- nvidia-utils (nvidia-smi) - for NVIDIA GPU stats (VRAM, clock, load)
- Root access or udev rules for USB device access

### GPU Support

- **NVIDIA**: Full support (temp, load, clock, VRAM) via nvidia-smi
- **AMD/Intel**: Temperature only via hwmon sensors (no VRAM metrics implemented)

## Installation

### Quick Install (Arch/Debian/Ubuntu/Fedora)

```bash
git clone <repository-url>
cd lm360
./install.sh          # Run as regular user (prompts for sudo when needed)
# or
./install.sh --enable # Auto-enable and start service
```

The installer:
- Detects your distribution and installs dependencies
- Creates `lm360` group and adds current user
- Installs to `/usr/local/bin/lm360` and `/usr/local/lib/lm360`
- Installs systemd service (manual enable unless --enable flag)
- Backs up conflicting `deepcool-lm` services to prevent dual USB ownership
- Sets group-based IPC socket permissions (0660) for `lm360` group members

**After installation**: Relogin or run `newgrp lm360` to activate group membership.

### Dry Run

Test installation without making changes:

```bash
sudo ./install.sh --dry-run
```

### Uninstall

```bash
cd lm360
sudo ./install.sh uninstall
```

Preserves `/var/lib/lm360/theme` state.

## Usage

### Start Service

```bash
sudo systemctl enable --now lm360
sudo systemctl status lm360
```

### CLI Commands

```bash
# Check service status
sudo lm360 status

# Start monitoring (when service not running)
sudo lm360 start --interval 2.0

# Brightness control
sudo lm360 brightness up
sudo lm360 brightness down

# Screen on/off (deterministic black frame, not backlight power)
sudo lm360 off
sudo lm360 on

# Theme switching (light/dark)
sudo lm360 theme dark
sudo lm360 theme light

# Layout management
sudo lm360 layout list
sudo lm360 layout set monitor

# Generate preview (headless, no USB)
lm360 preview --output preview.png --theme light
```

### Permissions

The service runs as root with group `lm360`. IPC socket (`/var/run/lm360/lm360.sock`) uses group-based access control (mode 0660). 

**To use `lm360` commands without sudo:**
1. Add your user to the `lm360` group (installer does this automatically)
2. Relogin or run: `newgrp lm360`
3. Test: `lm360 status`

Users not in the `lm360` group must use `sudo lm360 <command>`.

## Architecture

```
lm360/
├── display.py      # PIL rendering, RGB565 encoding
├── system.py       # CPU/GPU sensor collection
├── driver.py       # USB protocol (VID 0x3633, PID 0x0026)
├── layouts.py      # Extensible layout registry
├── service.py      # IPC server, display state
└── cli.py          # Command-line interface
```

### USB Protocol

- **Frame**: 13-byte header + 153600-byte RGB565 framebuffer (320×240 LE)
- **Init**: `aa 01 00 09 29 91`
- **Brightness Up**: `aa 04 00 06 03 61 00 d2 46` (relative)
- **Brightness Down**: `aa 04 00 06 03 1d 00 e6 0b` (relative)
- **Frame Header**: `aa 08 00 00 01 00 58 02 00 2c 01 bc 11`

**Note**: No absolute brightness level is known. Screen "off" is a black frame; true backlight power-off requires untested protocol.

## Current Layout

The default monitor layout (no header) displays:

- **Section 01 / CPU**: Model, temperature (large), load %, clock speed (GHz), RAM used/total/% with bar
- **Section 02 / GPU**: Model, temperature (large), load %, clock speed (GHz), VRAM used/total/% with bar

Bars turn red at ≥90% usage.

## Sensor Detection

- **CPU Temp**: k10temp (AMD Ryzen Tdie/Tctl), coretemp (Intel Package)
- **GPU Temp**: nvidia-smi, amdgpu/radeon edge, intel xe/i915
- **CPU Model**: `/proc/cpuinfo`
- **GPU Model**: nvidia-smi or lspci
- **RAM**: psutil virtual_memory (total - available)
- **VRAM**: nvidia-smi only (AMD/Intel not implemented)

## Known Limitations

1. **No absolute brightness setting**: Protocol only supports relative up/down steps
2. **Screen "off" is not backlight power**: Sends black frame; backlight remains on
3. **No VRAM for AMD/Intel GPUs**: Only NVIDIA supported via nvidia-smi
4. **No pump/fan/ARGB control**: This driver only controls the LCD
5. **Hardware not verified in cloud environment**: Package built from tested source but not re-verified on hardware

## Testing

Run unit tests:

```bash
python -m pytest tests/ -v
# or
python -m unittest discover tests/
```

Tests cover:
- Display rendering (layout, themes, RGB565 encoding)
- System sensor parsing and normalization
- USB protocol (mock-based, no hardware)
- IPC service state management

## Provenance

This project is derived from:

1. **daedlock/deepcool-lm** (original upstream, MIT declared in README, no LICENSE file)
   - Commit: 93d3c4396742683f273ae64c6368caa58c7819a0 (2025-11-21)
   - USB protocol reverse-engineering

2. **Nk-YMZ/deepcool-lm** (fork with AMD support, MIT per PKGBUILD)
   - Release: v1.3.0 (2026-08-11, commit 0cf51209a76fc8436449a0bef9e0beb16e6a58be)
   - Added AMD hardware detection, improved sensors
   - Chinese comments, AI-assisted development (per README)

See `THIRD_PARTY.md` for full provenance details.

**License Status**: Upstream repositories declare MIT license in metadata but lack formal LICENSE files with copyright holders/years. This package preserves attribution and does not claim ownership of derived code. Users should verify license compatibility for their use case.

## License

Follows upstream MIT declaration. See `THIRD_PARTY.md` for attribution.

## Contributing

- Test other LM-series models (LM240, LM280) and report compatibility
- Add VRAM support for AMD/Intel GPUs
- Implement additional layouts
- Test absolute brightness protocol
- Test true backlight power-off command

## Troubleshooting

### Device not found

```bash
lsusb | grep 3633:0026
```

Should show `ID 3633:0026`. If missing, check physical USB connection.

### No temperature readings

```bash
sudo sensors-detect  # Answer YES to save
sudo systemctl enable --now lm_sensors
sensors              # Verify output
```

### Permission denied

Service requires root. Check:

```bash
sudo systemctl status lm360
sudo journalctl -u lm360 -n 50
```

### Conflicting services

Installer detects and backs up `deepcool-lm` and `deepcool-lm-arkui` services. Restore from `/var/backups/lm360-install-*/`.

## References

- [DeepCool LM360 Product Page](https://www.deepcool.com/products/Cooling/cpuliquidcoolers/LM360-M-ARGB-White-CPU-Liquid-Cooler/2024/19077.shtml)
- USB VID 0x3633 (DC), PID 0x0026 (LM-Series)
- Resolution: 320×240, RGB565 little-endian
