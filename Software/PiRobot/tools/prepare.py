#!/usr/bin/env python3
"""Prepare an isolated deployment workspace. Prints commands unless --apply is given."""
import argparse
from pathlib import Path
import platform
import shlex
import subprocess
import sys
from common import BACKEND, BACKEND_PYTHON, ROOT, ROS_SETUP, SDK_REVISION, SDK_URL, WORKSPACE, execute

PACKAGES = ["git", "build-essential", "cmake", "python3-venv", "python3-yaml",
            "python3-colcon-common-extensions", "ros-jazzy-ros-base",
            "ros-jazzy-tf2-ros", "ros-jazzy-rmw-fastrtps-cpp"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--install-system-packages", action="store_true",
                        help="Use sudo apt; official ROS 2 apt repository must already be configured")
    parser.add_argument("--viewer", action="store_true", help="Also install RViz; skip Pi backend environment")
    args = parser.parse_args()
    release = platform.freedesktop_os_release()
    if release.get("ID") != "ubuntu" or release.get("VERSION_ID") != "24.04":
        raise ValueError("Supported deployment target is Ubuntu 24.04")
    if platform.machine() not in {"aarch64", "x86_64"}:
        raise ValueError("Use 64-bit ARM on Pi 5, or x86_64 Ubuntu on the laptop")
    def run(command, **kwargs):
        execute(command, apply=args.apply, **kwargs)
    if args.install_system_packages:
        run(["sudo", "apt-get", "update"])
        packages = PACKAGES + (["ros-jazzy-rviz2"] if args.viewer else [])
        run(["sudo", "apt-get", "install", "-y", *packages])
    if args.apply and not ROS_SETUP.is_file():
        raise ValueError("Install ROS 2 Jazzy first (see README, official apt repository setup)")
    vendor = WORKSPACE / "src/sllidar_ros2"
    if vendor.exists():
        if not (vendor / ".git").exists():
            raise ValueError(f"Refusing to overwrite non-git directory: {vendor}")
        revision = subprocess.check_output(["git", "-C", str(vendor), "rev-parse", "HEAD"], text=True).strip()
        dirty = subprocess.check_output(["git", "-C", str(vendor), "status", "--porcelain"], text=True).strip()
        if revision != SDK_REVISION or dirty:
            raise ValueError("Existing lidar driver differs from pinned clean revision; preserve/review it manually")
    else:
        run(["git", "clone", "--no-checkout", SDK_URL, str(vendor)])
        run(["git", "-C", str(vendor), "checkout", "--detach", SDK_REVISION])
    # Explicit system Python avoids a user-managed Python shadowing ROS dependencies.
    build = ["/usr/bin/colcon", "build", "--symlink-install", "--packages-up-to", "omni_bringup",
             "--cmake-args", "-DPython3_EXECUTABLE=/usr/bin/python3", "-DPYTHON_EXECUTABLE=/usr/bin/python3"]
    run(["bash", "-c", "source /opt/ros/jazzy/setup.bash && " + shlex.join(build)], cwd=WORKSPACE)
    if not args.viewer:
        python = BACKEND_PYTHON
        if not python.exists():
            run(["/usr/bin/python3", "-m", "venv", str(BACKEND / ".venv-pi")])
        run([str(python), "-m", "pip", "install", "-r", str(BACKEND / "requirements.txt")])
    print("Prepared" if args.apply else "Dry run only. Re-run with --apply after reviewing commands.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        sys.exit(str(exc))
