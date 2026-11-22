import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from common import load_config, ros_environment


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "robot.json"
        self.config = {"ros_domain_id": 21, "http_port": 5000,
                       "lidar_port": "/dev/serial/by-id/lidar-test",
                       "motor_port": "/dev/ttyAMA-test",
                       "mount_config": "/tmp/measured-mount.yaml"}

    def load(self, config, **kwargs):
        self.path.write_text(json.dumps(config))
        return load_config(self.path, **kwargs)

    def test_valid_config(self):
        result = self.load(self.config)
        self.assertEqual(result["mount_config"], "/tmp/measured-mount.yaml")
        self.assertEqual(result["ros_domain_id"], 21)

    def test_viewer_needs_only_domain(self):
        self.assertEqual(self.load({"ros_domain_id": 21}, viewer=True), {"ros_domain_id": 21})

    def test_invalid_domains(self):
        for domain in [True, -1, 102, 1.5, "21", None]:
            with self.subTest(domain=domain), self.assertRaises(ValueError):
                self.load({**self.config, "ros_domain_id": domain})

    def test_invalid_device_or_port(self):
        for changes in [{"http_port": True}, {"http_port": 80},
                        {"motor_port": "ttyAMA0"}, {"lidar_port": "/dev/REPLACE_ME"},
                        {"mount_config": ""}, {"mount_config": 3}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.load({**self.config, **changes})

    def test_same_device_aliases_rejected(self):
        target = Path(self.directory.name) / "device"
        target.touch()
        a = Path(self.directory.name) / "a"
        b = Path(self.directory.name) / "b"
        a.symlink_to(target)
        b.symlink_to(target)
        # Paths must be /dev paths in deployment; patch resolution, not hardware.
        with patch("common.os.path.realpath", return_value=str(target)):
            with self.assertRaises(ValueError):
                self.load(self.config)

    def test_network_domain_is_explicit(self):
        with patch.dict("os.environ", {"ROS_LOCALHOST_ONLY": "1", "ROS_DOMAIN_ID": "0"}):
            env = ros_environment(21)
            self.assertEqual(env["ROS_DOMAIN_ID"], "21")
            self.assertEqual(env["ROS_AUTOMATIC_DISCOVERY_RANGE"], "SUBNET")
            self.assertNotIn("ROS_LOCALHOST_ONLY", env)


if __name__ == "__main__":
    unittest.main()
