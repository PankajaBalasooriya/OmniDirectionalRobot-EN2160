# omni_bringup

ROS 2 Jazzy lidar-only bringup. No motor, odometry, navigation, or mapping nodes.
The upstream `sllidar_ros2` package must be available in the sourced environment.
C1 serial speed is fixed at 460800 baud; frames are fixed to `base_link` and
`laser`, and scans are published on `/scan`.

Copy `config/lidar_mount.yaml` to an absolute path outside the install tree.
Measure the transform from `base_link` to the laser scan frame (not merely the
housing): xyz in meters, roll/pitch/yaw in radians using ROS fixed-axis RPY.
Check axes and signs and explicitly approve it with `mount_calibrated: true`.
The installed example is uncalibrated and intentionally refuses to launch.
Zero values are placeholders, not a calibration. Do not approve them blindly.

After building and sourcing the workspace:

```sh
ros2 launch omni_bringup robot.launch.py mount_config:=/absolute/path/lidar_mount.yaml serial_port:=/dev/serial/by-id/DEVICE
```

Use a real stable serial alias (`by-id` or `by-path`), with OS permissions already
configured. The launch validates configuration before scheduling any nodes; it
does not probe/open the port during validation.

On a laptop in the same ROS domain/network, run only:

```sh
ros2 launch omni_bringup view.launch.py
```

This starts RViz alone, not the lidar or TF publisher. RViz uses `base_link`,
TF (including `laser`), and best-effort volatile `/scan` QoS. The robot must
supply the measured static TF and scan data.

Pure validation tests (no ROS or hardware required):

```sh
/usr/bin/python3 -m unittest discover -s test
```
