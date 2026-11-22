#!/usr/bin/env python3
"""Read-only deployment checks. Never opens serial or commands a motor."""
import argparse
import os
from pathlib import Path
import platform
import sys
from common import BACKEND, BACKEND_PYTHON, ROOT, ROS_SETUP, WORKSPACE, load_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/robot.json")
    parser.add_argument("--viewer", action="store_true")
    args = parser.parse_args()
    failures = []
    def check(label, okay):
        print(f"{'OK' if okay else 'FAIL'}: {label}")
        if not okay:
            failures.append(label)
    release = platform.freedesktop_os_release()
    check("Ubuntu 24.04", release.get("ID") == "ubuntu" and release.get("VERSION_ID") == "24.04")
    check("64-bit ARM or x86", platform.machine() in {"aarch64", "x86_64"})
    check("ROS 2 Jazzy installed", ROS_SETUP.is_file())
    check("workspace built", (WORKSPACE / "install/setup.bash").is_file())
    config = load_config(args.config, viewer=args.viewer)
    print(f"ROS domain: {config['ros_domain_id']} (must match laptop)")
    if args.viewer:
        check("desktop display", bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")))
    else:
        check("backend environment", BACKEND_PYTHON.is_file())
        for key in ("lidar_port", "motor_port"):
            path = config[key]
            check(f"{key} exists: {path}", Path(path).exists())
            check(f"{key} readable/writable", os.access(path, os.R_OK | os.W_OK))
        check("mount file exists", Path(config["mount_config"]).is_file())
        sys.path.insert(0, str(WORKSPACE / "src/omni_bringup"))
        from omni_bringup.config_validation import load_mount, validate_serial_port
        try:
            validate_serial_port(config["lidar_port"])
            load_mount(config["mount_config"])
            check("stable lidar path and approved mount", True)
        except (ValueError, OSError) as exc:
            check(f"stable lidar path and approved mount: {exc}", False)
    print("No UART opened. No robot safety certification implied by these checks.")
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as exc:
        sys.exit(str(exc))
