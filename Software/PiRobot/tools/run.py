#!/usr/bin/env python3
"""Explicit foreground launch commands; no automatic motor arming."""
import argparse
import sys
from pathlib import Path
from common import BACKEND, BACKEND_PYTHON, ROOT, execute, load_config, require_device, ros_command, ros_environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("component", choices=["lidar", "view", "backend"])
    parser.add_argument("--config", type=Path)
    parser.add_argument("--uart", action="store_true", help="Backend: open motor UART, writes disabled by default")
    parser.add_argument("--enable-hardware-motion", action="store_true",
                        help="Explicit opt-in ONLY after motor firmware safety fixes and bench checks")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    viewer = args.component == "view"
    path = args.config or ROOT / "config" / ("rviz.json" if viewer else "robot.json")
    if args.component != "backend" and (args.uart or args.enable_hardware_motion):
        parser.error("UART/motion options apply only to backend")
    if args.enable_hardware_motion and not args.uart:
        parser.error("--enable-hardware-motion requires --uart")
    config = load_config(path, viewer=viewer)
    environment = ros_environment(config["ros_domain_id"])
    if args.component == "lidar":
        if not args.dry_run:
            require_device(config["lidar_port"])
        command = ros_command(["ros2", "launch", "omni_bringup", "robot.launch.py",
                               "serial_port:=" + config["lidar_port"],
                               "mount_config:=" + config["mount_config"]])
        execute(command, env=environment, apply=not args.dry_run)
    elif viewer:
        command = ros_command(["ros2", "launch", "omni_bringup", "view.launch.py"])
        execute(command, env=environment, apply=not args.dry_run)
    else:
        python = BACKEND_PYTHON
        if not python.is_file():
            raise ValueError("Run tools/prepare.py --apply to create PiBackend's .venv-pi")
        command = [str(python), "-m", "pi_backend", "--http-port", str(config["http_port"])]
        if args.uart:
            if not args.dry_run:
                require_device(config["motor_port"])
            command += ["--live", "--port", config["motor_port"]]
        if args.enable_hardware_motion:
            command += ["--enable-hardware-motion"]
        execute(command, cwd=BACKEND, apply=not args.dry_run)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        sys.exit(str(exc))
