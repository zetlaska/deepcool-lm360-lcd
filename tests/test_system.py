"""Tests for system monitoring."""

import unittest

from lm360.system import (
    _normalize_cpu_identity,
    _normalize_frequency,
    _normalize_gpu_model,
    _normalize_mib,
    _normalize_percent,
    _normalize_temperature,
    _parse_pci_gpu_identities,
)


class SystemTests(unittest.TestCase):
    def test_normalize_cpu_identity_amd(self):
        brand, model = _normalize_cpu_identity("AMD Ryzen 9 9900X 12-Core Processor")
        self.assertEqual(brand, "AMD")
        self.assertEqual(model, "Ryzen 9 9900X")

    def test_normalize_cpu_identity_intel(self):
        brand, model = _normalize_cpu_identity("Intel(R) Core(TM) i9-14900K CPU @ 3.20GHz")
        self.assertEqual(brand, "Intel")
        self.assertIn("i9-14900K", model)

    def test_normalize_gpu_model_strips_vendor(self):
        self.assertEqual(_normalize_gpu_model("NVIDIA GeForce RTX 5090", "NVIDIA"), "RTX 5090")
        self.assertEqual(_normalize_gpu_model("GeForce RTX 4090", "NVIDIA"), "RTX 4090")

    def test_normalize_gpu_model_handles_brackets(self):
        self.assertEqual(_normalize_gpu_model("VGA [RTX 5090]", "NVIDIA"), "RTX 5090")

    def test_normalize_temperature_valid(self):
        self.assertEqual(_normalize_temperature(72.5), 72.5)
        self.assertEqual(_normalize_temperature("65"), 65.0)

    def test_normalize_temperature_invalid(self):
        self.assertIsNone(_normalize_temperature(None))
        self.assertIsNone(_normalize_temperature("invalid"))
        self.assertIsNone(_normalize_temperature(300))

    def test_normalize_percent_valid(self):
        self.assertEqual(_normalize_percent(85.7), 85.7)
        self.assertEqual(_normalize_percent("42"), 42.0)

    def test_normalize_percent_invalid(self):
        self.assertIsNone(_normalize_percent(150))
        self.assertIsNone(_normalize_percent(-10))

    def test_normalize_frequency_valid(self):
        self.assertEqual(_normalize_frequency(5200), 5.2)
        self.assertEqual(_normalize_frequency("3600"), 3.6)

    def test_normalize_frequency_invalid(self):
        self.assertIsNone(_normalize_frequency(None))
        self.assertIsNone(_normalize_frequency(200000))

    def test_normalize_mib_valid(self):
        self.assertEqual(_normalize_mib(16384), 16384)
        self.assertEqual(_normalize_mib("2048"), 2048.0)

    def test_normalize_mib_invalid(self):
        self.assertIsNone(_normalize_mib(-100))
        self.assertIsNone(_normalize_mib(1e10))

    def test_parse_pci_gpu_identities_nvidia(self):
        lspci_output = '0000:01:00.0 "VGA compatible controller" "NVIDIA Corporation" "Device 2684" -r02 -p00 "NVIDIA Corporation" "Device 17fc"'
        identities = _parse_pci_gpu_identities(lspci_output)
        self.assertEqual(len(identities), 1)
        self.assertEqual(identities[0][0], "NVIDIA")

    def test_parse_pci_gpu_identities_amd(self):
        lspci_output = '0000:03:00.0 "VGA compatible controller" "Advanced Micro Devices, Inc. [AMD/ATI]" "Navi 31" "Advanced Micro Devices, Inc. [AMD/ATI]" "Device 0e3e"'
        identities = _parse_pci_gpu_identities(lspci_output)
        self.assertEqual(len(identities), 1)
        self.assertEqual(identities[0][0], "AMD")

    def test_parse_pci_gpu_identities_intel(self):
        lspci_output = '0000:00:02.0 "VGA compatible controller" "Intel Corporation" "Alder Lake-S GT1" "Intel Corporation" "Device 4692"'
        identities = _parse_pci_gpu_identities(lspci_output)
        self.assertEqual(len(identities), 1)
        self.assertEqual(identities[0][0], "Intel")


if __name__ == "__main__":
    unittest.main()
