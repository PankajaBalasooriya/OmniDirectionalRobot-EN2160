import copy
from pathlib import Path
import tempfile
import unittest

from omni_bringup.config_validation import load_mount, validate_mount, validate_serial_port


class MountTests(unittest.TestCase):
    def setUp(self):
        self.good = {"mount_calibrated": True, "xyz": [0, 0.1, -0.2], "rpy": [0, 0, 1.57]}

    def test_valid(self):
        self.assertEqual(validate_mount(self.good)["xyz"], [0.0, 0.1, -0.2])

    def test_unapproved_and_strict_boolean(self):
        for value in (False, "true", 1, None):
            data = dict(self.good, mount_calibrated=value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_mount(data)

    def test_vectors(self):
        for key in ("xyz", "rpy"):
            for value in ([0, 0], [0, 0, float("nan")], [float("inf"), 0, 0],
                          [True, 0, 0], ["0", 0, 0], None):
                data = copy.deepcopy(self.good)
                data[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    validate_mount(data)

    def test_schema(self):
        for data in (None, [], {}, dict(self.good, frame_id="other")):
            with self.assertRaises(ValueError):
                validate_mount(data)

    def test_default_is_blocked(self):
        default = Path(__file__).resolve().parents[1] / "config" / "lidar_mount.yaml"
        with self.assertRaises(ValueError):
            load_mount(default)

    def test_load_absolute(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "mount.yaml"
            config.write_text("mount_calibrated: true\nxyz: [0, 0, 0]\nrpy: [0, 0, 0]\n")
            self.assertEqual(load_mount(config)["rpy"], [0.0] * 3)
        with self.assertRaises(ValueError):
            load_mount("relative.yaml")

    def test_serial_stable_alias(self):
        for port in ("/dev/serial/by-id/lidar", "/dev/serial/by-path/platform-usb"):
            self.assertEqual(validate_serial_port(port), port)
        for port in ("", "/dev/ttyUSB0", "relative", "/dev/serial/by-id/../ttyUSB0"):
            with self.assertRaises(ValueError):
                validate_serial_port(port)
