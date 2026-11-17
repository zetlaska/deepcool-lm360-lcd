# Third-Party Provenance and Attribution

This project (`lm360`) is derived from existing open-source work on DeepCool LM-series LCD drivers.

## Upstream Sources

### 1. daedlock/deepcool-lm (Original)

- **Repository**: https://github.com/daedlock/deepcool-lm
- **Commit**: 93d3c4396742683f273ae64c6368caa58c7819a0 (2025-11-21)
- **Author**: dlock
- **License Declared**: MIT (per README badge and "MIT License - Feel free to use and modify" statement)
- **License File**: None present in repository
- **Copyright Notice**: None present in repository

**Contribution**:
- Original USB protocol reverse-engineering
- Initial display driver implementation
- System monitoring interface

**Status**: README declares MIT license but repository lacks formal LICENSE file with copyright holder and year. No copyright notices in source files.

### 2. Nk-YMZ/deepcool-lm (Fork with AMD Support)

- **Repository**: https://github.com/Nk-YMZ/deepcool-lm
- **Release**: v1.3.0 (2026-08-11)
- **Commit**: 0cf51209a76fc8436449a0bef9e0beb16e6a58be
- **Maintainer**: Nk-YMZ
- **License Declared**: MIT (per PKGBUILD `license=('MIT')` and AUR metadata)
- **License File**: None present in repository
- **Copyright Notice**: None present in repository

**Contribution**:
- AMD hardware support (k10temp, amdgpu sensors)
- Improved CPU/GPU identity detection via `/proc/cpuinfo` and `lspci`
- Sensor normalization and validation
- Theme system (light/dark)
- Chinese language comments/strings

**Notes**:
- Fork README states development was mainly AI-assisted
- Code comments and some strings in Chinese
- AUR package `deepcool-lm-arkui` (conflicts with `deepcool-lm`)

## Derived Work

This `lm360` package is a clean reimplementation based on the above sources:

**Changes from upstream**:
- Reorganized into maintainable Python package structure
- Separated concerns (display, system, driver, service, CLI, layouts)
- Added extensible layout registry
- Improved deterministic screen on/off
- Changed IPC socket permissions to 0600 (root-only, was 0666)
- Removed custom image upload feature
- English documentation and comments
- Comprehensive unit tests
- Single-script installer with distro detection
- Explicit VRAM/RAM display (inherited from Nk-YMZ modifications)

**Preserved from upstream**:
- USB protocol bytes (frame header, brightness commands, init query)
- RGB565 encoding logic
- Font loading paths (DejaVu Sans)
- Sensor detection strategies (k10temp, coretemp, nvidia-smi)
- CPU/GPU model normalization regexes
- Display layout structure (two sections, temperature, stats, memory bars)
- Theme color palettes

## License Uncertainty

**Important**: Neither upstream repository contains a formal LICENSE file with copyright holder names and years. Both declare "MIT" only in metadata files (README badge, PKGBUILD).

This package:
- Preserves attribution to both upstream projects
- Does not claim blanket ownership of derived code
- Follows upstream MIT declaration
- **Does not provide legal clearance for release**: Users must verify license compatibility for their use case and consider contacting upstream authors for clarification

## Attribution Requirement

Any use of this package or its derivatives should include:

```
Based on deepcool-lm by daedlock (https://github.com/daedlock/deepcool-lm)
and Nk-YMZ (https://github.com/Nk-YMZ/deepcool-lm)
```

## Hardware Protocol

The USB protocol was reverse-engineered from the official Windows DeepCool software and documented by the upstream authors. This package uses that protocol specification.

## No Warranty

This software is provided as-is, without warranty of any kind. See upstream MIT license declarations for details.

---

**Package Author's Note**: This provenance document explicitly acknowledges the license file gap in upstream repositories. Formal license text with copyright holders should be confirmed before considering this package legally cleared for public release or redistribution.
