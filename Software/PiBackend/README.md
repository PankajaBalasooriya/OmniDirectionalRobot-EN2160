# Raspberry Pi 5 backend

Separate backend for the existing STM32 motor board. Existing software and firmware are untouched.
Python 3.11+; Flask HTTP API; one serial worker owns the UART. Simulation is the default.
Includes a same-origin browser UI for discrete moves and raw status. ROS, waypoint execution,
and continuous velocity control are not included.

## Safety / compatibility

**Do not run powered motion with the currently reviewed motor firmware.** It has braking,
Y-wait, direction and stop/disable defects. The existing protocol has no STOP command or
link-loss watchdog. A Pi timeout, process exit, serial disconnect, or HTTP STOP cannot halt it.
Use a physical emergency stop that removes motor drive power. Bench-test with drive power
removed first. The hardware opt-in flag is an operator acknowledgment, not a safety fix.

Commands use the existing `[command:uint8, value:uint8]` protocol, 115200 baud, 8N1,
no flow control. Values are raw firmware arguments, **not speed, centimeters, or calibrated
angles**. Firmware currently passes them to distance/angle routines; verify units on hardware.
Backward-left is known to execute the wrong direction. No conversion/workaround is hidden here.

Telemetry is `[type:uint8, value:uint8]`: A1 completion, A2/A3 raw distances,
A4 current, A5 encoder, A6 system status. These values are not calibrated feedback.
Only one move is outstanding. Further moves receive 409; there is no command backlog or retry.
A1=1 releases the busy state but only means *firmware-reported* completion, not standstill.
Malformed telemetry or completion timeout latches a fault; manually inspect the robot before
restarting. The unframed protocol cannot reliably reject stale replies, detect byte loss, or
correlate completion with a command. Pi software cannot repair these firmware limitations.

## Direct UART wiring

- Pi TX (GPIO14, physical pin 8) → motor board MCU UART RX.
- Pi RX (GPIO15, physical pin 10) ← motor board MCU UART TX.
- Pi GND (e.g. physical pin 6) ↔ motor board signal GND.
- **3.3 V TTL only.** Verify the board connector schematic and voltage levels first.
  Do not connect RS485 A/B, RS232, 5 V signals, or motor supply voltage to Pi GPIO.
- Do not connect power pins between boards. Power Pi 5 from a suitable regulated supply.
- Keep wires short and away from motor/power wiring; direct UART is not differential/noise resistant.

Use `sudo raspi-config`: disable the serial login shell and enable serial hardware.
Reboot if prompted. Give the service user serial permission (usually `dialout`; log in again).
Confirm the selected device actually routes to header GPIO14/15 before connecting motors.
**On Pi 5, `/dev/serial0` may refer to the dedicated debug UART, not the 40-pin header.**
Header UART may require a board-appropriate device-tree overlay. Consult the installed Raspberry
Pi OS documentation, inspect `/dev/ttyAMA*` and `/dev/serial*`, and verify with a loopback test.
The backend deliberately requires an explicit `--port` in live mode and changes no OS settings.

## Install / test / run

From this folder, using uv:

```sh
uv sync
uv run python -m unittest discover -s tests -v
node tests/test_ui.cjs  # optional UI contract checks; requires Node.js
uv run python -m pi_backend
```

Without uv, use:

```sh
python3 -m venv .venv
.venv/bin/pip install 'Flask>=3.1,<4' 'pyserial>=3.5,<4'
.venv/bin/python -m pi_backend
```

API listens only on `127.0.0.1:5000`, debug/reloader off, no permissive CORS.
For laptop access use an authenticated SSH tunnel rather than exposing an unauthenticated API:

```sh
ssh -L 5000:127.0.0.1:5000 USER@PI_ADDRESS
```

Then open `http://127.0.0.1:5000` locally for the browser controls.

### Browser controls

Select a translation or rotation direction, enter a raw value (1–255), and click **Send one move**.
Selecting a direction does not move the robot. There are no keyboard shortcuts, held-button
motion, command repeats, or automatic retries. The page polls status once per second and disables
submission when offline, busy, faulted, or hardware motion is disabled. Live mode also requires
a browser safety acknowledgment; this is not a replacement for backend safeguards or firmware fixes.
Backward-left is blocked in the live UI because of the known direction bug; the raw API remains
protocol-compatible and does not apply this UI restriction. No software STOP button is offered:
the page explicitly directs the operator to the physical emergency stop.
Simulation acceptance is labeled separately from live UART acceptance. Neither is proof of
physical completion. If a request times out, delivery is uncertain; inspect the robot before retrying.
Assets are local, with no CDN dependencies or cross-origin API requests.

```sh
curl http://127.0.0.1:5000/api/status
curl http://127.0.0.1:5000/api/commands
curl -X POST http://127.0.0.1:5000/api/move -H 'Content-Type: application/json' \
  -H 'X-Backend-ID: COPY_backend_id_FROM_STATUS' -H 'X-Expected-Mode: simulation' \
  -d '{"direction":"forward","value":1}'
curl -X POST http://127.0.0.1:5000/api/stop
```

Move requests must include `X-Backend-ID` and `X-Expected-Mode` headers from the latest
`/api/status` response. A backend restart or mode mismatch returns 409 without accepting motion.
These headers bind operator intent to an instance; they are not authentication.
The browser ignores out-of-order status responses and latches failed move submissions until
an operator explicitly acknowledges robot inspection. It never retries automatically.

`/api/move` returns 202 for simulation or accepted UART work, not execution confirmation.
`/api/stop` always returns 501 and explicitly says a physical emergency stop is required.

For UART receive-only bench inspection (never writes motion):

```sh
uv run python -m pi_backend --live --port /dev/YOUR_VERIFIED_UART
```

Only after firmware safety fixes and physical validation, opt into motion by additionally
passing `--enable-hardware-motion`. Default completion timeout is 120 seconds; override with
`--completion-timeout SECONDS`. Timeout closes UART and refuses further commands, **not motor power**.
There is no automatic reconnect. Never run multiple backend processes on the same UART.

## Initial design choices

Defaults: 115200 baud to match motor USART3, loopback HTTP port 5000, 120-second completion
timeout (an operational fault threshold, not a safety deadline). Valid raw values: 1–255;
zero is rejected because it is not a valid STOP and can retain stale profile state.
No motor constants, firmware files, or existing GUI files were changed.
