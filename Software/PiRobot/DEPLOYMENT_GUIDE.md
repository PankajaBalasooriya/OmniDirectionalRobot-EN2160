# Omni robot deployment guide

**Platform:** Raspberry Pi 5 · Ubuntu 24.04 LTS arm64 · ROS 2 Jazzy · RPLIDAR C1 · existing STM32 motor controller

**Guide date:** 2026-11-22

**Audience:** operator deploying the robot and a laptop visualization station.

> **Safety boundary:** Start with motor drive power disconnected. The current motor firmware
> has known braking, direction, blocking-move, and stop defects. The software in this repository
> does not make powered motion safe. UART disconnect, browser close, Ctrl+C, and Pi shutdown
> cannot stop a move already executing on the STM32. Use a physical emergency stop that removes
> motor drive power. Do not enable powered motion until the firmware safety checks in this guide pass.

## Contents

1. [Outcome and architecture](#1-outcome-and-architecture)
2. [Hardware and information checklist](#2-hardware-and-information-checklist)
3. [Prepare Ubuntu and SSH](#3-prepare-ubuntu-and-ssh)
4. [Install the ROS foundation](#4-install-the-ros-foundation)
5. [Transfer the software](#5-transfer-the-software)
6. [Build on the Pi and laptop](#6-build-on-the-pi-and-laptop)
7. [Wire and identify devices](#7-wire-and-identify-devices)
8. [Measure and configure the lidar mount](#8-measure-and-configure-the-lidar-mount)
9. [Verify stationary lidar in RViz](#9-verify-stationary-lidar-in-rviz)
10. [Run the browser in simulation](#10-run-the-browser-in-simulation)
11. [Bench-test motor UART](#11-bench-test-motor-uart)
12. [Gate powered motion](#12-gate-powered-motion)
13. [Daily startup and shutdown](#13-daily-startup-and-shutdown)
14. [Troubleshooting](#14-troubleshooting)
15. [Tests and acceptance record](#15-tests-and-acceptance-record)
16. [Next stages: odometry, mapping, navigation](#16-next-stages-odometry-mapping-navigation)

## 1. Outcome and architecture

The initial deployment delivers **stationary live lidar scans on a laptop** and a **browser
interface in simulation**, with a separate path for motor UART bench testing.

```text
Laptop: Ubuntu 24.04 + ROS 2 Jazzy
  ├─ RViz ◄──── ROS 2 DDS over trusted LAN ────┐
  └─ Browser ─── SSH tunnel ───────────────────┤
                                             ▼
                              Raspberry Pi 5
                              Ubuntu 24.04 arm64
                              ├─ ROS 2 C1 driver
                              ├─ base_link → laser static transform
                              └─ browser backend + one UART worker
                                    │                 │
                              USB   │                 │ 3.3 V TTL UART
                                    ▼                 ▼
                              RPLIDAR C1       STM32 motor controller
                                                     │
                                                Motor drivers
```

### What exists

| Component | Repository location | Role |
|---|---|---|
| Deployment tools | `Software/PiRobot/tools/` | Setup, preflight, foreground launch |
| ROS bringup | `Software/PiRobot/ros2_ws/src/omni_bringup/` | C1, measured transform, RViz |
| Browser backend/UI | `Software/PiBackend/` | Discrete commands, raw telemetry, simulation |
| Existing motor firmware | `Software/MotorController/Motor_controller/` | STM32 motion/control loops; unchanged |

**Not implemented:** ROS velocity bridge, usable wheel odometry, localization, SLAM, Nav2,
autonomous collision avoidance, or lidar-triggered emergency stopping. The lidar view is not a map.
The Flask backend and lidar ROS node are separate processes; the browser does not show lidar scans.

### Defaults and assumptions

- Pi: Ubuntu 24.04 **arm64**, not an x86 image.
- Laptop: Ubuntu 24.04 with a graphical desktop and Jazzy.
- C1: USB serial, **460800 baud**, Standard scan mode.
- Motor board: verified MCU UART, **115200 baud, 8N1**, existing two-byte protocol.
- ROS domain: **21**, an example isolation setting; match it on both computers.
- Browser backend: loopback HTTP **5000**, simulation by default.
- Move completion timeout: **120 seconds**; operational fault detection, not a safe stopping deadline.
- No physical mount offsets, motor distance units, or UART connector pinout are assumed.

## 2. Hardware and information checklist

### Required hardware

- [ ] Pi 5, active cooling, and suitable regulated power supply.
- [ ] Reliable microSD or SSD for Ubuntu.
- [ ] RPLIDAR C1 and its USB adapter/cable.
- [ ] Rigid, level lidar mount and cable strain relief.
- [ ] Existing STM32 motor board, verified firmware version, and connector schematic.
- [ ] Short UART wiring away from motor power wiring.
- [ ] Physical emergency stop and a way to disconnect motor drive power separately.
- [ ] Laptop and trusted LAN; avoid guest/client-isolated Wi-Fi.

### Fill in before deployment

| Item | Actual value |
|---|---|
| Pi SSH username | ____________________ |
| Pi hostname / IP | ____________________ |
| Pi repository directory | ____________________ |
| Laptop repository directory | ____________________ |
| C1 stable USB serial path | ____________________ |
| Motor UART device / header routing | ____________________ |
| Motor connector TX / RX / GND pins | ____________________ |
| Confirmed UART logic voltage | ____________________ |
| Motor firmware revision | ____________________ |
| Lidar measured xyz, meters | ____________________ |
| Lidar measured rpy, radians | ____________________ |
| Physical emergency-stop test date | ____________________ |

## 3. Prepare Ubuntu and SSH

1. Install **Ubuntu Server 24.04 LTS arm64** supported for Pi 5. Desktop also works, but
   RViz can run on the laptop, so the Pi does not need a desktop.
2. Enable SSH, create a normal user, configure networking, and complete first boot.
3. Use active cooling. Verify the Pi is not suffering undervoltage or thermal throttling.
4. Keep motor drive power disconnected during installation and initial checks.

**Pi terminal:**

```bash
cat /etc/os-release
uname -m
hostname -I
```

Expected: Ubuntu `24.04`, architecture `aarch64`, and a reachable LAN address.

**Laptop terminal:** replace `USER` and `PI_ADDRESS`:

```bash
ssh USER@PI_ADDRESS
```

Keep the verified SSH host key. Prefer SSH keys once initial login works. Do not expose SSH,
Flask, or ROS DDS directly to the public Internet.

**Pass condition:** SSH is reliable and the Pi runs the expected OS/architecture.

## 4. Install the ROS foundation

Configure the **official Jazzy apt repository** on both machines using the maintained instructions:

https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html

Follow the Ubuntu locale, repository, and signing-key steps there. Do not use Humble packages,
Ubuntu 22.04 instructions, or an unreviewed root-install script. Back up existing OS configuration
before changing repository or boot settings. Skip repository changes if Jazzy already works.

The project's preparation tool can install the required ROS packages **after the official apt
repository is configured**. It does not configure apt sources itself.

After installation, check in a terminal on each machine:

```bash
source /opt/ros/jazzy/setup.bash
ros2 --help
```

Do not install ROS dependencies into the old Windows `venv` or into the agent's environment.
The build explicitly uses `/usr/bin/python3` to match Ubuntu's ROS dependencies.

## 5. Transfer the software

The new `Software/PiBackend` and `Software/PiRobot` directories must actually be present on the Pi.
If they have not been committed and pushed, a plain `git clone` will **not** include them.

Options:

- Commit/review/push the code, then clone/pull it on the Pi; or
- Copy the two application folders with rsync.

**Laptop terminal, from the repository root:**

```bash
ssh USER@PI_ADDRESS 'mkdir -p ~/omni-robot/Software'
rsync -av --exclude='.venv/' --exclude='.venv-pi/' --exclude='__pycache__/'   --exclude='ros2_ws/build/' --exclude='ros2_ws/install/' --exclude='ros2_ws/log/'   --exclude='ros2_ws/src/sllidar_ros2/'   Software/PiBackend Software/PiRobot USER@PI_ADDRESS:~/omni-robot/Software/
```

Do not use `--delete` against an existing configured Pi deployment. For updates, preserve/back up
`config/robot.json`, `config/rviz.json`, and measured mount YAML first. The rsync command does not
include generated environments/builds, but it will update source files, including the mount template.

Do not copy the repository's old Windows `venv`. Build environments locally on each architecture.

For the examples below, the Pi checkout is `~/omni-robot`. Change the path to your actual directory.

## 6. Build on the Pi and laptop

### Pi

```bash
cd ~/omni-robot/Software/PiRobot
/usr/bin/python3 tools/prepare.py --install-system-packages
```

This is a **dry run**: inspect the displayed commands. Then apply:

```bash
/usr/bin/python3 tools/prepare.py --install-system-packages --apply
```

This fetches a pinned official Slamtec driver, builds the ROS workspace, and creates
`Software/PiBackend/.venv-pi` with the pinned dependencies in `requirements.txt`.

### Laptop

From the laptop's `Software/PiRobot` directory:

```bash
/usr/bin/python3 tools/prepare.py --install-system-packages --viewer
/usr/bin/python3 tools/prepare.py --install-system-packages --viewer --apply
```

The viewer option installs RViz and skips the Pi backend environment. It still builds the ROS
workspace. Omit `--install-system-packages` if dependencies are already installed.

### Build behavior

- Setup never opens hardware or starts motor commands.
- The driver commit is recorded in `tools/common.py`.
- Existing dirty, different, or incomplete driver checkouts are not overwritten.
- If a clone fails, stop the owning setup process before inspecting it. Preserve/rename the
  incomplete `ros2_ws/src/sllidar_ros2` directory, then rerun; do not delete unrelated work.
- Native system Python avoids the previously observed `catkin_pkg` failure caused by a shadow Python.

**Pass condition:** setup exits successfully; both `sllidar_ros2` and `omni_bringup` build.

## 7. Wire and identify devices

### 7.1 C1: USB only for this deployment

Connect the C1 USB adapter to the Pi. Keep its scanning plane clear of the chassis and payload.

**Pi terminal:**

```bash
lsusb
ls -l /dev/serial/by-id/
ls -l /dev/serial/by-path/
```

Record the C1 adapter's stable `/dev/serial/by-id/...` path. The alias identifies its USB adapter;
it does not by itself prove a C1 is attached. Confirm lidar identity/health through the driver.

### 7.2 Motor board: direct UART

**Verify the connector schematic and logic voltage before wiring.** These are Pi physical header
pin numbers, not an assertion about your motor-board connector layout:

| Pi signal | Pi physical pin | Connect to verified motor-board signal |
|---|---:|---|
| GPIO14 TX | 8 | MCU UART RX |
| GPIO15 RX | 10 | MCU UART TX |
| GND | e.g. 6 | Signal GND |

- Signals must be **3.3 V TTL**.
- Never connect RS485 A/B, RS232, 5 V UART, motor voltage, or supply pins to Pi GPIO.
- Do not tie board supply outputs together. Never power motors from Pi.
- Keep motor and logic power/ground design suitable for noise and current; verify ground potential.
- Keep UART wires short, secure, and away from motor/PWM wiring.

### 7.3 Enable the actual Pi 5 header UART

Use the documentation for your installed Ubuntu/Pi firmware image to enable a UART routed to
GPIO14/15 and disable its serial login console. Back up boot configuration before editing.

**Do not assume `/dev/serial0` is the header UART:** on Pi 5 it may refer to the dedicated debug
UART connector. Exact overlays/device names depend on the image. Do not blindly copy an overlay
for a different Pi model or OS.

Inspect:

```bash
ls -l /dev/serial* /dev/ttyAMA* /dev/ttyUSB*
```

With the motor board disconnected, verify the selected device and GPIO routing using a UART
loopback test. Only then connect the verified motor-board UART.

### 7.4 Permissions and ownership

```bash
id
sudo usermod -aG dialout "$USER"
```

Log out and back in after changing groups. Use your normal user for the application. Avoid
world-writable device permissions and unnecessary root execution.

Before opening a device, check whether another process owns it:

```bash
fuser /dev/YOUR_VERIFIED_DEVICE
```

One process per serial device. Do not run a standalone C1 SDK test alongside the ROS C1 driver.

**Pass condition:** C1 USB and motor UART are distinct verified devices with appropriate access.
No software check can certify the physical header wiring for you.

## 8. Measure and configure the lidar mount

### 8.1 Copy local configuration once

**Pi, from `Software/PiRobot`:**

```bash
cp -n config/robot.example.json config/robot.json
```

Edit it with your actual values:

```json
{
  "ros_domain_id": 21,
  "lidar_port": "/dev/serial/by-id/REPLACE_WITH_ACTUAL_C1_ADAPTER",
  "motor_port": "/dev/REPLACE_WITH_VERIFIED_HEADER_UART",
  "mount_config": "ros2_ws/src/omni_bringup/config/lidar_mount.yaml",
  "http_port": 5000
}
```

**These device strings are placeholders, not runnable defaults.** Both serial fields are required
by the current robot configuration, even when a component does not open both devices.
`mount_config` is relative to `Software/PiRobot`, or it may be an absolute path.

**Laptop, from its `Software/PiRobot`:**

```bash
cp -n config/rviz.example.json config/rviz.json
```

Set `ros_domain_id` to the same value as the Pi. Domain 21 is a project example, not a universal
ROS requirement. Use another matching domain if 21 conflicts with another robot.

### 8.2 Measure the transform

Pick and document the `base_link` origin, preferably the chassis kinematic reference point.
Use ROS axes: **X forward, Y left, Z up**.

Measure the C1 scan frame origin relative to that point:

- `xyz`: meters.
- `rpy`: roll, pitch, yaw in radians.
- Check the physical device's scan-frame orientation; do not infer it solely from the USB connector.

Edit:

```text
ros2_ws/src/omni_bringup/config/lidar_mount.yaml
```

The checked-in file has this structure:

```yaml
mount_calibrated: false
xyz: [0.0, 0.0, 0.0]
rpy: [0.0, 0.0, 0.0]
```

**Zeros are placeholders. Replace them with measurements.** Set `mount_calibrated: true` only
once the actual geometry is checked. Unapproved or invalid configuration blocks driver launch.
Use only the three documented keys; values must be finite numbers, not strings or booleans.

This static `base_link → laser` transform describes mounting geometry only. It is not odometry,
localization, or an estimate of robot motion.

## 9. Verify stationary lidar in RViz

Keep motor drive power disconnected. Leave the robot stationary.

### Pi terminal A

```bash
cd ~/omni-robot/Software/PiRobot
/usr/bin/python3 tools/preflight.py --config config/robot.json
/usr/bin/python3 tools/run.py lidar --config config/robot.json
```

Preflight checks both serial devices. It can fail for an unconfigured motor UART even if lidar-only
operation would be possible. Resolve configuration before claiming the whole deployment is ready.
The lidar launcher opens only the configured C1 device, not the motor UART.

### Laptop terminal A

From the laptop's `Software/PiRobot` directory:

```bash
/usr/bin/python3 tools/preflight.py --viewer --config config/rviz.json
/usr/bin/python3 tools/run.py view --config config/rviz.json
```

The viewer launcher starts RViz only. It does not start another C1 driver.

### Check in RViz

- Fixed frame: `base_link`.
- LaserScan topic: `/scan`.
- Lidar frame: `laser`.
- LaserScan reliability: Best Effort; durability: Volatile.
- Static transform: `base_link → laser`.

Place an object in front and then to the left. Verify direction and plausible distance. Check that
robot parts do not obscure the useful field of view and that scans remain stable while stationary.

### Optional terminal diagnosis

In a separate terminal on either computer, matching the configured domain:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=21
unset ROS_LOCALHOST_ONLY
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ros2 topic list
ros2 topic info /scan --verbose
ros2 topic echo /scan --once --field header --qos-reliability best_effort
```

A domain other than 21 must be substituted if you configured one. Seeing the topic name alone does
not prove messages are arriving; verify an actual message and the RViz display.

### Network requirements

- Both computers must reach each other on a trusted LAN.
- DDS uses multicast discovery and UDP traffic; guest Wi-Fi/client isolation can block it.
- Check firewall rules for your trusted interface/subnet. Do not disable all firewall protection.
- An SSH tunnel carries the browser connection, **not ordinary ROS DDS discovery**.
- Keep the ROS domain consistent; avoid stale ROS daemons started in another domain.

**Pass condition:** live `/scan` reaches RViz, transform status is healthy, and orientation/ranges
match physical observations. This is a scan view, not a SLAM map.

## 10. Run the browser in simulation

### Pi terminal B

```bash
cd ~/omni-robot/Software/PiRobot
/usr/bin/python3 tools/run.py backend --config config/robot.json
```

Default mode is simulation; no motor UART is opened by this command.

### Laptop terminal B

```bash
ssh -N -L 5000:127.0.0.1:5000 USER@PI_ADDRESS
```

Open **http://127.0.0.1:5000** on the laptop. Keep the tunnel running.

If local port 5000 is occupied, keep the Pi on port 5000 but use:

```bash
ssh -N -L 5001:127.0.0.1:5000 USER@PI_ADDRESS
```

Then open **http://127.0.0.1:5001**. If the Pi port itself is occupied, choose another
`http_port` in `robot.json` and match the tunnel destination to it.

### UI acceptance checks

- [ ] Clear **SIMULATION** label.
- [ ] Direction selection alone sends no move.
- [ ] Send submits exactly one discrete move.
- [ ] Values must be integers 1–255, in raw firmware units.
- [ ] Simulation acceptance is not presented as physical movement.
- [ ] Offline/busy/fault states block submission.
- [ ] Restart/mode mismatch rejects stale requests.
- [ ] Uncertain delivery requires inspection acknowledgment before another submission.
- [ ] No misleading software emergency-stop control.

The Flask backend binds loopback only, with debug/reloader disabled and no permissive CORS.
The current development server is for supervised bringup, not a hardened unattended deployment.

## 11. Bench-test motor UART

**Keep motor drive power disconnected.** Confirm firmware identity, connector pinout, voltage,
and header UART routing before connecting the board.

Stop the simulation backend with Ctrl+C before starting another backend instance.

### Receive-only mode

```bash
/usr/bin/python3 tools/run.py backend --config config/robot.json --uart
```

This opens the configured motor UART at 115200 baud, but the backend rejects motion writes unless
explicitly enabled. UART open/close may affect adapter control lines; verify no board reset/boot
signals are unintentionally wired to those lines.

The board may be silent until it receives commands. An open port or an idle UI does not prove
end-to-end protocol compatibility. Use a logic analyzer/oscilloscope or a controlled bench test
with motor drive power physically disconnected to verify electrical traffic.

### Current protocol limitations

- Commands are two bytes: `[command:uint8, value:uint8]`.
- Values are raw firmware arguments, not calibrated centimeters, degrees, or velocity.
- A single move may block firmware command handling.
- Telemetry completion is firmware-reported, not proof of physical standstill.
- There is no STOP command, watchdog, framing, checksum, or transaction correlation.
- Backend faults latch rather than retrying/replaying a physical command.

See [PiBackend protocol and API documentation](../PiBackend/README.md).

## 12. Gate powered motion

### Mandatory focused firmware work

Before powered motion, fix and bench-test:

1. Braking target and stopping-distance calculation.
2. Y move waiting on the wrong profile.
3. Backward-left direction.
4. Stop/disable being overwritten by periodic control.
5. Interruptible STOP handling and a robot-side communication watchdog.

A new STOP/watchdog protocol also requires matching backend code and tests. The current backend
will continue to report STOP as unsupported until such support is implemented and verified.
Do not mistake the hardware opt-in flag for these fixes.

### Controlled test sequence

1. Prove the physical emergency stop removes motor drive power.
2. Use a secured bench setup; verify each wheel/encoder direction.
3. Verify speed limits, profile completion, fault handling, and watchdog stopping.
4. Confirm distance/angle units and calibrate against measurements.
5. Test disconnects and process failures using an approved safe setup.
6. Only then test slow discrete moves in a clear area, with an operator at the emergency stop.

**After those conditions pass**, the existing opt-in command is:

```bash
/usr/bin/python3 tools/run.py backend --config config/robot.json   --uart --enable-hardware-motion
```

The live UI additionally requires safety acknowledgment and blocks backward-left due to its known
firmware defect. The raw API remains protocol-compatible and does not enforce that UI restriction.
Do not use the API to bypass it on uncorrected firmware.

**Pass condition:** documented physical test evidence establishes safe motion and stopping.
Software compilation and mocked tests alone cannot satisfy this gate.

## 13. Daily startup and shutdown

### Startup: stationary bringup

1. Inspect power, wiring, mounts, emergency stop, and the test area.
2. Keep motor drive power disconnected for lidar/simulation checks.
3. Boot Pi; verify SSH and serial device identity/permissions.
4. Run preflight.
5. Start Pi lidar terminal A.
6. Start laptop RViz and verify scans/TF.
7. Start Pi simulation backend terminal B.
8. Start the laptop SSH tunnel and open the browser.
9. Proceed to hardware testing only under the powered-motion gate above.

### Shutdown

1. If motion is active or uncertain, use the physical emergency stop and disconnect motor drive power.
2. Ctrl+C the Pi backend. This stops the process, **not an already-executing STM32 move**.
3. Ctrl+C the Pi lidar launcher; check that the lidar driver exits and scanning stops.
4. Close RViz and stop the SSH tunnel.
5. Shut down Ubuntu cleanly:

   ```bash
   sudo shutdown -h now
   ```

6. Wait for shutdown before removing Pi power.

Closing RViz does not stop the Pi lidar driver. Optional boot services for sensing and the
simulation UI are now available: follow [AUTO_START.md](AUTO_START.md) after manual bringup passes.
They are not installed by ordinary preparation or cloning, never open the motor UART, and never
arm motors. Native Pi installation and a reboot acceptance check must still be performed.

## 14. Troubleshooting

| Symptom | Check / action |
|---|---|
| `ros-jazzy-*` packages unavailable | Ubuntu version and official Jazzy apt repository setup |
| `catkin_pkg` import error during build | Use supplied setup tool; it explicitly selects `/usr/bin/python3` |
| Git clone hangs/fails | Inspect network; stop the owning setup process before preserving/renaming its incomplete checkout and retrying |
| Existing driver checkout refused | It is dirty/different/incomplete; preserve it and review rather than overwriting |
| `Permission denied` on serial | `dialout`, logout/login, device owner/ACL; avoid world-writable permissions |
| Device busy | `fuser` the actual path; stop only the confirmed owning process |
| Wrong serial device after reboot | Use C1 by-id/by-path alias; verify motor header routing separately |
| C1 health/query fails | Correct adapter, 460800 baud, USB cable/power, exclusive ownership |
| Mount launch refused | Enter measured xyz/rpy, strict YAML booleans/numbers, and approval flag |
| Invalid mount YAML error | Correct indentation/syntax and finite numeric values; YAML syntax errors are reported as readable validation errors |
| RViz sees no `/scan` | Driver logs, domain ID, LAN discovery, firewall/client isolation |
| RViz transform error | `base_link → laser` publisher and matching frame names |
| Scans rotated/mirrored | Verify physical scan-frame orientation and measured yaw; do not invent offsets |
| Browser cannot connect | Pi backend running, SSH tunnel destination/ports, loopback URL |
| Backend says hardware disabled | Expected in receive-only mode; do not bypass before safety fixes |
| Move returns 409 | Busy controller or stale backend instance/mode; inspect status, never blindly replay |
| Move result uncertain | Inspect the robot physically; acknowledgment does not undo a delivered move |
| Completion timeout/fault | Robot may still move; physical stop first, inspect UART/firmware before restarting |
| STOP returns 501 | Expected: existing motor protocol has no STOP support |

Never run two backend processes on one UART. Never point the motor backend at the C1 adapter.
The device checks reject aliasing the configured lidar but cannot identify every physical device.

## 15. Tests and acceptance record

### Automated checks

From `Software/PiRobot`:

```bash
/usr/bin/python3 -m unittest discover -s tests -v
PYTHONPATH=ros2_ws/src/omni_bringup /usr/bin/python3 -m unittest discover   -s ros2_ws/src/omni_bringup/test -v
```

From `Software/PiBackend`, after Pi preparation:

```bash
.venv-pi/bin/python -m unittest discover -s tests -v
node tests/test_ui.cjs
```

The Node.js check is optional and requires Node.js; the deployed browser/backend does not require
Node.js to run. These tests do not command hardware.

### Validation already performed during development

- Current computer: C1 identity/health query and a short successful physical scan test.
- Current computer: ROS driver published `/scan` and opened RViz.
- Native x86 Ubuntu/Jazzy: official C1 driver and `omni_bringup` workspace build succeeded.
- 6 deployment tests, 7 mount/config tests, 13 backend tests, and browser contract checks passed.
- Independent deployment review found no new blocking code defect.

**Not yet demonstrated:** native Pi ARM deployment, final robot wiring, measured mount alignment,
reliable powered motion, watchdog stopping, wheel odometry, or autonomous navigation.

### Record on the actual robot

| Gate | Date / operator / evidence |
|---|---|
| Ubuntu, SSH, cooling and power verified | ____________________ |
| Native Pi workspace build passed | ____________________ |
| C1 identity/health and stable device path | ____________________ |
| Motor voltage/pinout/header loopback verified | ____________________ |
| Measured mount and front/left orientation check | ____________________ |
| Laptop `/scan` and TF healthy | ____________________ |
| Browser simulation accepted | ____________________ |
| UART bench traffic verified with drive power off | ____________________ |
| Firmware safety fixes and matching backend support | ____________________ |
| Physical emergency stop and watchdog tested | ____________________ |
| Controlled low-speed physical motion accepted | ____________________ |

## 16. Next stages: odometry, mapping, navigation

Only after safe manual motion:

1. Add reliable velocity commands and measured wheel feedback.
2. Calibrate wheel radius, encoder scale/signs, and mecanum geometry.
3. Publish actual wheel odometry and `odom → base_link`; do not synthesize motion from command acceptance.
4. Add an IMU if available, with measured frame alignment and validated calibration.
5. Record and inspect synchronized scans/odometry before mapping.
6. Integrate SLAM, then localization and Nav2 with a verified robot footprint and stopping behavior.
7. Test progressively in a controlled environment; lidar is not a safety-rated substitute for a physical stop.

The critical path is **Pi deployment → verified scans/TF → safe motor interface → usable odometry → mapping/navigation**.
No deadline or performance claim is assumed.

## References and source of truth

- [Project deployment README](README.md)
- [Browser backend/API](../PiBackend/README.md)
- [ROS package](ros2_ws/src/omni_bringup/README.md)
- [ROS 2 Jazzy Ubuntu installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
- [Official Slamtec ROS 2 driver](https://github.com/Slamtec/sllidar_ros2)
- Executable behavior: `tools/prepare.py`, `tools/preflight.py`, `tools/run.py`, and backend source.

This guide changes no motor firmware, electrical constants, boot settings, or live configuration.
Keep measured configuration and hardware acceptance evidence with the deployed robot.
