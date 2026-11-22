# Omni robot: Pi 5 deployment (stationary lidar milestone)

For the complete operator walkthrough, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).
For tested links and remaining hardware gaps, see [CONNECTION_VERIFICATION.md](CONNECTION_VERIFICATION.md).
For optional Pi boot sensing and simulation UI services, see [AUTO_START.md](AUTO_START.md).

Target: **Ubuntu 24.04 LTS arm64 + ROS 2 Jazzy** on Raspberry Pi 5.
Laptop: Ubuntu 24.04 + Jazzy + RViz. The Pi runs the C1 and the browser backend;
the STM32 retains all motor control. This is working deployment code, **not autonomous navigation**.
No `/cmd_vel` bridge, wheel odometry, localization, SLAM, Nav2, or collision-stop capability is claimed.

## What is included

- `tools/prepare.py`: reviewed-command/dry-run setup; pinned official C1 driver; native colcon build;
  isolated backend `.venv-pi` with locked Python dependencies.
- `tools/preflight.py`: read-only OS, configuration and device permission checks.
- `tools/run.py lidar`: C1 and measured `base_link → laser` transform.
- `tools/run.py view`: laptop RViz only; never opens UART or starts another lidar driver.
- `tools/run.py backend`: browser UI, simulation default; explicit UART receive-only option.
- `ros2_ws/src/omni_bringup`: ROS launch/config/visualization package.

All setup is operator-run. Nothing automatically installs packages, edits Pi boot files, opens
serial ports, starts at boot, or arms motors simply because this repository is cloned.

## 1. OS and ROS foundation (Pi and laptop)

Install Ubuntu 24.04 **64-bit ARM** on Pi 5 (Server is fine), with active cooling and a suitable
regulated power supply. Enable SSH and connect both machines to the same trusted LAN.
Install/configure the official ROS 2 Jazzy apt repository using the current Ubuntu instructions:
https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html

This repository deliberately does not download an unverified root-install shell script or replace
existing apt sources. The optional apt step below assumes that official ROS repository is configured.
If ROS is already installed, skip OS/repository changes. Keep your existing configuration backed up
before making OS-level changes. Run the deployment tools as your normal user, not as root.

Copy this repository to the Pi, e.g. using git or rsync. Do not copy the old Windows `venv` or
Linux `.venv` environments across architectures. Run all following commands from `Software/PiRobot`.

On the Pi, first inspect commands, then apply them:

```sh
/usr/bin/python3 tools/prepare.py --install-system-packages
/usr/bin/python3 tools/prepare.py --install-system-packages --apply
```

On the laptop:

```sh
/usr/bin/python3 tools/prepare.py --install-system-packages --viewer
/usr/bin/python3 tools/prepare.py --install-system-packages --viewer --apply
```

If dependencies already exist, omit `--install-system-packages`. The official driver is checked
out at a fixed commit recorded in `tools/common.py`. An existing dirty/different driver checkout
is never overwritten. A `.venv-pi` is created for the backend without altering `.venv` or Windows `venv`.
An Internet connection is needed for git and Python packages. No robot hardware is accessed during setup.

## 2. Wiring and serial devices

### C1: keep USB

Connect the C1 using its USB adapter to a Pi USB port. It uses **460800 baud**, Standard scan mode.
Mount it level, rigidly, with its horizontal scanning plane above obstructing parts of the chassis.
Keep cables and payload out of the field of view. Top/front is suitable if unobstructed.

### Motor board: dedicated 3.3 V UART

- Pi GPIO14 TX (physical pin 8) → verified motor MCU UART RX.
- Pi GPIO15 RX (physical pin 10) ← verified motor MCU UART TX.
- Signal ground ↔ Pi GND (e.g. physical pin 6).
- **Verify the actual connector schematic and 3.3 V TTL levels before wiring.** Do not connect
  RS485 A/B, RS232, 5 V signals, motor power, or board supply pins to GPIO.
- Keep wires short and away from motor power. Pi and motors need suitable independent regulated
  supplies and a safe grounding design. Never power motors from Pi.

Enable a Pi 5 header UART and disable the serial login console using instructions for your actual
Ubuntu/Pi firmware image. **`/dev/serial0` on Pi 5 may be the dedicated debug UART**, not pins 8/10.
Do not guess device names or blindly edit overlays. Verify pin routing with a loopback test before
attaching the motor board. C1 USB serial and motor UART must resolve to different devices.

Inspect devices:

```sh
ls -l /dev/serial/by-id/ /dev/serial/by-path/
ls -l /dev/ttyAMA* /dev/ttyUSB*
```

Add your normal account to `dialout` if needed, then log out/in (or reboot):

```sh
sudo usermod -aG dialout "$USER"
```

Use the C1's stable `/dev/serial/by-id/...` path. Never assign the lidar's `/dev/ttyUSB0` to the
motor backend. Do not grant world-writable serial permissions. Only one process may own each device.

## 3. Configure measured mount and device paths

Copy examples once; preserve existing files rather than overwriting them:

```sh
cp -n config/robot.example.json config/robot.json
cp -n config/rviz.example.json config/rviz.json
```

Edit `config/robot.json` on the Pi with the actual C1 USB path and verified motor UART device.
`mount_config` is relative to `Software/PiRobot` unless absolute. Both devices must be configured,
but the lidar launcher does not open the motor UART. Domain **21** is an example isolated ROS domain;
use the same domain on the laptop, and a different domain from unrelated robots.

Measure the C1 optical scan origin relative to your chosen robot `base_link` origin:

- ROS convention: X forward, Y left, Z up.
- `xyz` in meters; `rpy` roll/pitch/yaw in radians.
- Prefer base_link at the robot's kinematic reference (e.g. chassis center between wheels).
- Verify the lidar forward direction from the device markings and actual scan observations.

Edit `ros2_ws/src/omni_bringup/config/lidar_mount.yaml` to the **measured** values and set
`mount_calibrated: true` only after checking them. Default zeros are placeholders; launch refuses
uncalibrated configuration. This transform is mounting geometry, not robot localization or odometry.

## 4. Stationary lidar first

With motor drive power disconnected:

Pi terminal:

```sh
/usr/bin/python3 tools/preflight.py --config config/robot.json
/usr/bin/python3 tools/run.py lidar --config config/robot.json
```

A missing motor UART can fail the full preflight even if a lidar-only test is otherwise ready;
resolve hardware configuration before claiming the whole robot is ready. The lidar command only
checks/opens the configured C1 device and validates its mount.

Laptop terminal (its `config/rviz.json` must use the same domain):

```sh
/usr/bin/python3 tools/preflight.py --viewer --config config/rviz.json
/usr/bin/python3 tools/run.py view --config config/rviz.json
```

RViz displays `/scan` in `base_link`, using `base_link → laser`. Place an object in front and
left of the robot to verify axis directions and plausible distance. This is a live **scan view**,
not a saved map. Closing RViz does not stop the driver; Ctrl+C the Pi lidar terminal to stop it.

Networking: both machines must reach each other; DDS discovery uses multicast and dynamic UDP
traffic. Set the same ROS_DOMAIN_ID, avoid guest/client-isolated Wi-Fi, and check host firewall rules
for your trusted LAN. Do not expose ROS DDS to the public Internet or disable firewalls globally.
The launch tools set ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET and unset legacy localhost-only settings.
A VPN/SSH tunnel alone is not sufficient for ordinary DDS multicast discovery.

## 5. Browser backend

A separate Pi terminal, **simulation default**:

```sh
/usr/bin/python3 tools/run.py backend --config config/robot.json
```

On the laptop create an SSH tunnel (replace the account/address):

```sh
ssh -L 5000:127.0.0.1:5000 USER@PI_ADDRESS
```

Open **http://127.0.0.1:5000**. Change the port on both sides if occupied.
The API remains loopback-only, with no debug mode or permissive CORS.

UART receive-only bench mode (no motion writes):

```sh
/usr/bin/python3 tools/run.py backend --config config/robot.json --uart
```

After physical bench checks **and motor firmware safety fixes**, the explicit opt-in is:

```sh
/usr/bin/python3 tools/run.py backend --config config/robot.json --uart --enable-hardware-motion
```

**Do not use that option for powered motion with the current repository motor firmware.**
Known issues include wrong-axis waits, wrong backward-left direction, broken braking and
nonpersistent stop/disable. The two-byte protocol has no STOP, watchdog, framing, command IDs,
or reliable physical completion feedback. Pi timeout, browser close, Ctrl+C, and serial disconnect
cannot stop an executing move. Have a physical emergency stop that removes motor drive power.
Backend acknowledges submission, not safe motion completion. No auto-repeat or retry is performed.

See `../PiBackend/README.md` for raw command units, API and protocol limitations.

## 6. Checks / next milestone

```sh
/usr/bin/python3 -m unittest discover -s tests -v
PYTHONPATH=ros2_ws/src/omni_bringup /usr/bin/python3 -m unittest discover -s ros2_ws/src/omni_bringup/test -v
```

For the backend tests, run them from `../PiBackend` so its module is importable:

```sh
cd ../PiBackend
.venv-pi/bin/python -m unittest discover -s tests -v
node tests/test_ui.cjs  # optional: Node.js required
```

Before mapping/navigation: fix the small STM32 safety defects, establish reliable velocity/stop
commands and measured wheel odometry, add IMU if available, then integrate SLAM/Nav2 with verified
TF and odometry. No invented wheel calibration or fabricated odometry is included here.
