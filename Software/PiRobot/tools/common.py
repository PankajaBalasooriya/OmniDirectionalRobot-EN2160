"""Shared deployment configuration. No hardware is opened here."""
import json
import os
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "ros2_ws"
BACKEND = ROOT.parent / "PiBackend"
BACKEND_PYTHON = BACKEND / ".venv-pi/bin/python"
ROS_SETUP = Path("/opt/ros/jazzy/setup.bash")
SDK_REVISION = "34300099fadfc772965962dec837bf436706188f"
SDK_URL = "https://github.com/Slamtec/sllidar_ros2.git"


def load_config(path, *, viewer=False):
    path = Path(path).expanduser().resolve()
    with path.open() as stream:
        config = json.load(stream)
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a JSON object")
    domain = config.get("ros_domain_id")
    if type(domain) is not int or not 0 <= domain <= 101:
        raise ValueError("ros_domain_id must be an integer from 0 to 101")
    if viewer:
        return config
    port = config.get("http_port")
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("http_port must be an integer from 1024 to 65535")
    for key in ("lidar_port", "motor_port"):
        value = config.get(key)
        if not isinstance(value, str) or not value.startswith("/dev/") or "REPLACE" in value:
            raise ValueError(f"Set {key} to the verified /dev device path")
    if os.path.realpath(config["lidar_port"]) == os.path.realpath(config["motor_port"]):
        raise ValueError("Lidar and motor UART must be different devices")
    mount = config.get("mount_config")
    if not isinstance(mount, str) or not mount:
        raise ValueError("mount_config is required")
    config["mount_config"] = str((ROOT / mount).resolve())
    return config


def ros_environment(domain):
    environment = os.environ.copy()
    environment["ROS_DOMAIN_ID"] = str(domain)
    # LOCALHOST is inherited by ROS processes in some desktop setups: explicitly use LAN.
    environment.pop("ROS_LOCALHOST_ONLY", None)
    environment["ROS_AUTOMATIC_DISCOVERY_RANGE"] = "SUBNET"
    return environment


def ros_command(arguments):
    setup = WORKSPACE / "install/setup.bash"
    for path in (ROS_SETUP, setup):
        if not path.is_file():
            raise ValueError(f"Missing {path}; prepare/build this workspace first")
    return ["bash", "-c", f"source {shlex.quote(str(ROS_SETUP))} && "
            f"source {shlex.quote(str(setup))} && exec " + shlex.join(arguments)]


def require_device(path):
    if not Path(path).exists():
        raise ValueError(f"Serial device does not exist: {path}")
    if not os.access(path, os.R_OK | os.W_OK):
        raise ValueError(f"Serial device is not readable/writable: {path}; check dialout permissions")


def execute(command, *, cwd=None, env=None, apply=True):
    print("+ " + shlex.join(str(item) for item in command), flush=True)
    if apply:
        subprocess.run(command, cwd=cwd, env=env, check=True)
