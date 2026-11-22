# Connection verification

Verified 2026-11-22 on the current Ubuntu laptop. This is not a Pi hardware acceptance certificate.
No physical motor port was opened or commanded. Firmware and control constants were not changed.

| Connection | Result | Evidence / limit |
|---|---|---|
| C1 USB → current computer | PASS, physical | Adapter present; existing ROS driver owns /dev/ttyUSB0 |
| C1 → ROS /scan | PASS, physical | A fresh sensor_msgs/LaserScan header arrived, frame_id laser |
| Browser control logic → API | PASS, tests | UI contract checks, static assets, instance/mode guards, uncertainty latch |
| HTTP → backend → pyserial → virtual UART | PASS, integration | Real loopback HTTP server and POSIX pseudo-terminal, all ten command IDs |
| Virtual UART telemetry → backend → HTTP status | PASS, integration | A2/A3 distances and fragmented A1 completion parsed and returned |
| Backend packets → checked-in STM32 protocol | Compatible at byte-format level | Two bytes command/value, 115200 8N1; physical board firmware not queried |
| Deployment launcher → backend | PASS, contract | Simulation default, UART port selection, no implicit hardware arming |
| Deployment launcher → ROS package | PASS, contract/build | Required mount/device arguments passed; workspace compiled |
| Measured transform → ROS/RViz | BLOCKED intentionally | Default mount remains unapproved; launch correctly refuses before opening hardware |
| Pi → laptop DDS / RViz | NOT TESTED | No configured remote Pi or measured robot transform available |
| Pi GPIO UART → motor PCB | NOT TESTED | No verified Pi device, connector pinout, or physical motor link available |
| Motor command → actual wheel motion / feedback | NOT TESTED / unsafe | Existing firmware defects remain; no physical motion test attempted |
| Browser → lidar | NOT IMPLEMENTED | RViz, not the browser, displays lidar; these are separate processes |
| Lidar → motor stopping / navigation | NOT IMPLEMENTED | No collision-stop, odometry, SLAM, Nav2, or velocity bridge |

## Tests

- 14 backend tests passed, including a new real HTTP / pyserial pseudo-terminal round trip.
- 11 deployment/configuration/launcher tests passed.
- 7 mount validation tests pass in native ROS package testing (colcon reports one wrapper test).
- Node.js browser contract checks passed.
- Real ROS launch with the unapproved default mount refused as expected before starting nodes.
- Prior full native x86 workspace build succeeded; this does not establish ARM/Pi deployment.

New reproducible checks:

```bash
cd Software/PiBackend
uv run python -m unittest discover -s tests -v
node tests/test_ui.cjs
```

```bash
cd Software/PiRobot
/usr/bin/python3 -m unittest discover -s tests -v
source /opt/ros/jazzy/setup.bash
cd ros2_ws
colcon test --packages-select omni_bringup
colcon test-result --verbose
```

The pseudo-terminal simulates a UART peer; it does not execute STM32 firmware or validate its physics.
All ten wire IDs are tested, including backward-left, whose actual firmware behavior is known wrong.
A1 completion cannot prove physical standstill or correlate replies reliably in this unframed protocol.
The active firmware emits A1 completion and periodic A2/A3 distances. A4–A6 IDs are defined but
not actively emitted by the checked-in telemetry routine; their absence is not a broken connection.

## Physical wiring detail from checked-in firmware

The motor command/telemetry interface is **USART3**, not the USART2 Bluetooth/debug interface.
`Core/Src/stm32f4xx_hal_msp.c` configures **PC5 = USART3_RX** and **PB10 = USART3_TX**.
`Core/Src/main.c` configures USART3 at 115200, 8N1, no hardware flow control.

Subject to verifying the actual board connector/schematic and firmware:

- Pi GPIO14 TX, physical pin 8 → STM32 PC5 RX.
- Pi GPIO15 RX, physical pin 10 ← STM32 PB10 TX.
- Pi GND ↔ signal GND.

These are MCU signal assignments, not verified board connector pin numbers. Do not assume a
UART header exposes USART3. Confirm 3.3 V TTL levels and disconnect/isolate any RS485 receiver
output that would otherwise drive PC5 at the same time as Pi TX. Never connect GPIO to RS485 A/B.
No old SAM3X main-controller bridge is needed for the new backend's two-byte format.

## Deployment gaps on this computer

- No `config/robot.json` or `config/rviz.json` exists yet.
- No approved mount measurements have been entered.
- Deployment `.venv-pi` is not installed here; backend tests used its existing local `.venv`.
- No production browser backend was running at verification start; the temporary integration-test
  HTTP server was shut down after testing.
- Current physical C1 driver is the earlier standalone laptop launch, not the new measured robot
  bringup. Do not confuse its successful /scan with a verified robot base_link transform.

## Required to complete physical acceptance

1. Pi SSH hostname/IP and username, Ubuntu/Jazzy installed.
2. Actual C1 USB alias and verified Pi header UART routing/device.
3. Motor connector schematic/pinout, logic voltage, and deployed firmware revision.
4. Measured lidar xyz/rpy and local robot/viewer configurations.
5. Motor power disconnected for UART bench tests; physical emergency stop available.
6. Focused firmware safety fixes and matching backend support before powered motion.

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for the deployment sequence.

## Automatic-startup verification (2026-11-22)

- `tools/services.py` generates system units targeting `multi-user.target`: no login is required.
- Native `systemd-analyze verify` accepts both generated units.
- Installer defaults to dry-run and refuses missing prepared files, unapproved mounts, root service
  users, symlink unit targets, and updates under active units. Changed unit files are backed up.
- Boot UI starts the existing backend in simulation, with no `--uart`, `--live`, or hardware-motion
  flag. It does not access the motor board. Browser access remains through the SSH tunnel.
- Lidar service restarts sensing after process exit with a 5-second delay; TF/driver exits stop the
  whole launch. Explicit systemctl stop does not restart it. A live-but-stalled driver is not
  automatically detected; fresh /scan verification remains required.
- Mount YAML syntax errors are now reported as readable validation errors.
- 19 deployment/launcher/service tests, 8 mount tests, and 14 backend tests pass, plus UI checks.
- Services were not installed/enabled on this laptop. No Pi SSH address or configured native Pi
  environment was provided; actual installation, reboot startup, permissions and scan publication
  after boot remain unverified. See [AUTO_START.md](AUTO_START.md) for the acceptance procedure.
