"""Start only the C1 lidar and its measured static transform."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

from omni_bringup.config_validation import load_mount, validate_serial_port


def launch_nodes(context):
    # Validate everything before returning any process-start actions.
    mount = load_mount(LaunchConfiguration("mount_config").perform(context))
    port = validate_serial_port(LaunchConfiguration("serial_port").perform(context))
    x, y, z = mount["xyz"]
    roll, pitch, yaw = mount["rpy"]
    return [
        Node(package="tf2_ros", executable="static_transform_publisher",
             name="lidar_mount", arguments=[
                 "--x", str(x), "--y", str(y), "--z", str(z),
                 "--roll", str(roll), "--pitch", str(pitch), "--yaw", str(yaw),
                 "--frame-id", "base_link", "--child-frame-id", "laser"], output="screen"),
        Node(package="sllidar_ros2", executable="sllidar_node", name="sllidar_node",
             parameters=[{"channel_type": "serial", "serial_port": port,
                          "serial_baudrate": 460800, "frame_id": "laser",
                          "inverted": False, "angle_compensate": True,
                          "scan_mode": "Standard"}],
             remappings=[("scan", "/scan")], output="screen"),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("serial_port", description="Stable /dev/serial/by-id/... or by-path/... device"),
        DeclareLaunchArgument("mount_config", default_value=PathJoinSubstitution([
            FindPackageShare("omni_bringup"), "config", "lidar_mount.yaml"]),
            description="Absolute path to a measured, approved mount YAML"),
        OpaqueFunction(function=launch_nodes),
    ])
