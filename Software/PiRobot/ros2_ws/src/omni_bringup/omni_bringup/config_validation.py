"""Pure Python validation; never opens a device or starts ROS."""
import math
from pathlib import Path

import yaml


def validate_mount(data):
    if not isinstance(data, dict) or set(data) != {"mount_calibrated", "xyz", "rpy"}:
        raise ValueError("Mount YAML must contain only mount_calibrated, xyz, rpy")
    if type(data["mount_calibrated"]) is not bool:
        raise ValueError("mount_calibrated must be a YAML boolean")
    if not data["mount_calibrated"]:
        raise ValueError("Measure and approve the lidar mount before setting mount_calibrated: true")
    result = {}
    for key in ("xyz", "rpy"):
        values = data[key]
        if not isinstance(values, list) or len(values) != 3:
            raise ValueError(f"{key} must be a list of three finite numbers")
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise ValueError(f"{key} must contain finite numbers, not booleans")
        result[key] = [float(v) for v in values]
    return result


def load_mount(path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("mount_config must be an absolute path")
    try:
        with path.open(encoding="utf-8") as stream:
            return validate_mount(yaml.safe_load(stream))
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid mount YAML: {exc}") from exc


def validate_serial_port(port):
    # Do not resolve symlinks: the stable alias is what the driver should open.
    path = Path(port)
    if (not path.is_absolute() or path.parent.as_posix() not in
            ("/dev/serial/by-id", "/dev/serial/by-path") or path.name in ("", ".", "..")):
        raise ValueError("serial_port must be a stable /dev/serial/by-id/... or /dev/serial/by-path/... path")
    return port
