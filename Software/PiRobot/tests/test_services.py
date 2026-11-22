import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import services


class ServiceTests(unittest.TestCase):
    def test_units_start_lidar_and_simulation_only(self):
        units = services.render_units("operator", "/home/operator/robot/config.json",
                                      project="/home/operator/robot")
        self.assertEqual(set(units), {"omni-lidar.service", "omni-ui.service"})
        for name, text in units.items():
            self.assertIn("WantedBy=multi-user.target", text)
            self.assertIn("User=operator", text)
            self.assertIn("SupplementaryGroups=dialout", text)
            self.assertIn("KillMode=control-group", text)
            self.assertIn("KillSignal=SIGINT", text)
            start = next(line for line in text.splitlines() if line.startswith("ExecStart="))
            self.assertNotIn("--uart", start)
            self.assertNotIn("--enable-hardware-motion", start)
            self.assertNotIn("--live", start)
            self.assertIn(" backend " if name == "omni-ui.service" else " lidar ", start)
        self.assertIn("ROS_LOG_DIR=/var/lib/omni-lidar/log", units["omni-lidar.service"])
        self.assertIn("Restart=always", units["omni-lidar.service"])
        self.assertIn("Restart=on-failure", units["omni-ui.service"])

    def test_argument_escaping(self):
        self.assertEqual(services.quote('a%b$c"d\\e', executable=True),
                         '"a%%b$$c\\"d\\\\e"')
        units = services.render_units("operator", "/home/operator/a b/config.json",
                                      project="/home/operator/a b")
        self.assertIn('"/home/operator/a b/tools/run.py"', units["omni-ui.service"])
        with self.assertRaises(ValueError):
            services.quote("bad\nvalue")
        for project in ["/tmp/bad\npath", "/tmp/trailing ", "/tmp/back\\slash"]:
            with self.assertRaises(ValueError):
                services.render_units("operator", "/tmp/config", project=project)
        for user in ["root", "bad name", "operator\nUser=root"]:
            with self.assertRaises(ValueError):
                services.render_units(user, "/tmp/config")

    def test_existing_files_backed_up_and_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "omni-ui.service"
            path.write_text("original")
            services.write_units({path.name: "replacement"}, directory)
            backups = list(Path(directory).glob("*.backup-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), "original")
            services.write_units({path.name: "replacement"}, directory)
            self.assertEqual(len(list(Path(directory).glob("*.backup-*"))), 1)
            path.unlink()
            path.symlink_to(backups[0])
            with self.assertRaises(ValueError):
                services.write_units({path.name: "unsafe"}, directory)

    def test_default_is_dry_run_no_system_changes(self):
        operator = pwd.getpwuid(os.getuid())
        if operator.pw_uid == 0:
            self.skipTest("Needs normal account for installer dry-run")
        with patch.object(sys, "argv", ["services.py", "--user", operator.pw_name]), \
             patch.object(services, "validate_configuration"), \
             patch.object(Path, "is_file", return_value=True), \
             patch.object(services, "write_units") as write, \
             patch.object(services.subprocess, "run") as run:
            services.main()
        write.assert_not_called()
        run.assert_not_called()

    @unittest.skipUnless(shutil.which("systemd-analyze"), "systemd-analyze not installed")
    def test_native_systemd_parser(self):
        operator = pwd.getpwuid(os.getuid()).pw_name
        if operator == "root":
            self.skipTest("Need non-root account name")
        with tempfile.TemporaryDirectory(prefix="omni service % ") as directory:
            units = services.render_units(operator, "/tmp/test config.json")
            services.write_units(units, directory)
            result = subprocess.run(["systemd-analyze", "verify",
                                     *(str(Path(directory) / name) for name in units)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_default_mount_refuses_service_setup(self):
        with patch.object(services, "load_config", return_value={
            "lidar_port": "/dev/serial/by-id/test-device",
            "mount_config": str(services.WORKSPACE / "src/omni_bringup/config/lidar_mount.yaml")}):
            with self.assertRaisesRegex(ValueError, "Measure and approve"):
                services.validate_configuration("unused")

    def test_enable_requires_apply(self):
        with patch.object(sys, "argv", ["services.py", "--user", "operator", "--enable"]):
            with self.assertRaises(SystemExit) as error:
                services.main()
        self.assertEqual(error.exception.code, 2)

    def test_missing_environment_refuses_install(self):
        operator = pwd.getpwuid(os.getuid())
        if operator.pw_uid == 0:
            self.skipTest("Needs normal account")
        with patch.object(sys, "argv", ["services.py", "--user", operator.pw_name, "--apply"]), \
             patch.object(services, "validate_configuration"), \
             patch.object(Path, "is_file", return_value=False), \
             patch.object(services, "write_units") as write:
            with self.assertRaises(ValueError):
                services.main()
        write.assert_not_called()


if __name__ == "__main__":
    unittest.main()
