"""Verify deployment launcher wiring without starting ROS, HTTP, or hardware."""
import importlib.util
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("deployment_run", TOOLS / "run.py")
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)


class LauncherContractTests(unittest.TestCase):
    def invoke(self, args):
        config = {"ros_domain_id": 21, "http_port": 5000,
                  "lidar_port": "/dev/serial/by-id/virtual-c1",
                  "motor_port": "/dev/ttyAMA-virtual-motor",
                  "mount_config": "/tmp/test-only-approved-mount.yaml"}
        with patch.object(sys, "argv", ["run.py", *args]), \
             patch.object(run, "load_config", return_value=config), \
             patch.object(run, "require_device") as device, \
             patch.object(run, "ros_command", side_effect=lambda args: args), \
             patch.object(Path, "is_file", return_value=True), \
             patch.object(run, "execute") as execute:
            run.main()
        return execute.call_args, device

    def test_lidar_uses_only_lidar_and_measured_mount(self):
        call, device = self.invoke(["lidar"])
        device.assert_called_once_with("/dev/serial/by-id/virtual-c1")
        args = call.args[0]
        self.assertEqual(args[:4], ["ros2", "launch", "omni_bringup", "robot.launch.py"])
        self.assertIn("serial_port:=/dev/serial/by-id/virtual-c1", args)
        self.assertIn("mount_config:=/tmp/test-only-approved-mount.yaml", args)
        self.assertEqual(call.kwargs["env"]["ROS_DOMAIN_ID"], "21")

    def test_view_does_not_open_devices(self):
        call, device = self.invoke(["view"])
        device.assert_not_called()
        self.assertEqual(call.args[0], ["ros2", "launch", "omni_bringup", "view.launch.py"])
        self.assertEqual(call.kwargs["env"]["ROS_DOMAIN_ID"], "21")

    def test_backend_defaults_to_simulation(self):
        call, device = self.invoke(["backend"])
        device.assert_not_called()
        self.assertNotIn("--live", call.args[0])
        self.assertNotIn("--enable-hardware-motion", call.args[0])

    def test_uart_does_not_enable_motion(self):
        call, device = self.invoke(["backend", "--uart"])
        device.assert_called_once_with("/dev/ttyAMA-virtual-motor")
        self.assertIn("--live", call.args[0])
        self.assertIn("/dev/ttyAMA-virtual-motor", call.args[0])
        self.assertNotIn("--enable-hardware-motion", call.args[0])

    def test_hardware_motion_requires_uart(self):
        with patch.object(sys, "argv", ["run.py", "backend", "--enable-hardware-motion"]):
            with self.assertRaises(SystemExit) as error:
                run.main()
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
