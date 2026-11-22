# Pi boot services: sensing and browser UI

These **system** services start without an SSH session or desktop login:

| Unit | Boot behavior |
|---|---|
| `omni-lidar.service` | Starts the C1 ROS driver and approved `base_link → laser` transform |
| `omni-ui.service` | Starts the loopback browser backend in **simulation** |

**No motor UART is opened. No motor command or automatic arming is generated.**
The UI is usable through an SSH tunnel; it is not exposed on the Pi LAN address.
RViz stays on the laptop and is not started on the headless Pi.

## Prerequisites

Run the deployment guide first. On the **Pi**, as the normal operator:

1. Ubuntu 24.04 arm64, Jazzy, cooling, and reliable power.
2. `tools/prepare.py --apply` completed (not viewer-only), including `.venv-pi`.
3. Actual `config/robot.json`: verified distinct lidar/motor device paths, HTTP port, ROS domain.
   Motor path is required by configuration but never opened by these boot units.
4. Measured mount YAML with `mount_calibrated: true` and correct frame axes.
5. C1 stable by-id/by-path USB alias and correct 3.3 V motor wiring documented separately.
6. The operator can read the checkout and config, execute `.venv-pi/bin/python`, and access serial.
7. Stop standalone/manual lidar and backend processes to prevent port conflicts.
8. Keep motor drive power disconnected during initial deployment.

The installer validates prepared paths and mount approval but **does not open hardware**.
Its validation under sudo is not proof that the operator can access all files or that scans work.
Run operator preflight and manual sensing first. Neither root permission nor `systemctl active`
certifies robot safety or healthy scan publication.

Keep the checkout on a local filesystem available at boot, such as `/home/USER/omni-robot`.
Do not use an encrypted home that becomes available only after login, a removable drive that
is not mounted at boot, or a temporary directory. Do not move the checkout after installation.
The services execute the checkout directly; updating its code affects the next service restart.

## 1. Review generated services

From `Software/PiRobot` on the Pi, **without sudo**:

```bash
/usr/bin/python3 tools/preflight.py --config config/robot.json
/usr/bin/python3 tools/services.py --user "$USER" --config "$(pwd)/config/robot.json"
```

Default behavior is dry-run: prints both units and changes nothing.
There is deliberately no UART/arming flag in this installer.

Optional: generate files for native systemd syntax validation, without installing/enabling:

```bash
/usr/bin/python3 tools/services.py --user "$USER" --config "$(pwd)/config/robot.json"   --output-dir /tmp/omni-unit-review
systemd-analyze verify /tmp/omni-unit-review/omni-lidar.service /tmp/omni-unit-review/omni-ui.service
```

## 2. Install and enable on the Pi

Use your **normal account** in `--user`; `$USER` below expands before sudo changes identity:

```bash
sudo /usr/bin/python3 tools/services.py --user "$USER"   --config "$(pwd)/config/robot.json" --apply --enable
```

- Installs system units into `/etc/systemd/system/`.
- Runs service processes as the specified **non-root** user, with supplemental `dialout` group.
- Creates timestamped backups before replacing existing changed unit files.
- Refuses symlink unit targets and refuses updating active/activating units.
- Reloads systemd, enables both units for boot, and starts them now.
- To install without starting/enabling, omit `--enable`.

Do not run this on the development laptop unless you deliberately want that laptop to host services.
No services are installed simply by cloning the repository or running tests.

## 3. Check current operation

```bash
systemctl is-enabled omni-lidar.service omni-ui.service
systemctl status omni-lidar.service omni-ui.service --no-pager
journalctl -u omni-lidar.service -n 80 --no-pager
journalctl -u omni-ui.service -n 80 --no-pager
curl --fail http://127.0.0.1:5000/api/status
```

Adjust HTTP port if your config differs. Expected backend status:

```json
{"mode": "simulation", "state": "idle", "hardware_enabled": false, "stop_supported": false}
```

The actual response includes extra fields. Simulation does not prove motor connectivity.

Verify actual scan messages, not only `systemctl active`:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=21
unset ROS_LOCALHOST_ONLY
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ros2 topic echo /scan --once --field header --qos-reliability best_effort
```

Use the domain from your configuration. Open laptop RViz with `tools/run.py view` and verify
front/left orientation, distances, and TF. If a ROS daemon was previously started with another
domain/environment, use a fresh matching terminal and stop/restart that daemon if necessary.

### Laptop browser access

```bash
ssh -N -L 5000:127.0.0.1:5000 USER@PI_ADDRESS
```

Open `http://127.0.0.1:5000` on the laptop. Keep the tunnel running. If only the laptop's
local port is occupied, use `-L 5001:127.0.0.1:5000` and open port 5001 locally.
The boot backend remains a loopback-only Flask development server: suitable for supervised
bringup, not a hardened public or unsupervised production control service.

## 4. Reboot acceptance test

Only with motor drive power disconnected:

```bash
sudo reboot
```

After the Pi returns:

1. SSH in and check both units are enabled and running.
2. Inspect this boot's logs with `journalctl -b -u omni-lidar.service -u omni-ui.service`.
3. Confirm a fresh `/scan` message and correct laptop RViz view.
4. Reopen the SSH tunnel; verify UI explicitly says simulation.
5. Confirm no manual terminal was needed on the Pi to start either process.

No actual Pi reboot acceptance was performed by the agent; record these results on the robot.

## Lifecycle and failure behavior

- Units wait for the OS `network-online.target`; this is not proof that DDS peers are reachable.
- Lidar service retries every **5 seconds**, including after a clean launch exit.
- If the lidar driver or TF publisher exits, the whole launch stops so systemd can restart both.
- Missing USB device or invalid config causes a logged failure/retry, not motor activity.
- UI retries only on process failure and remains independent of lidar failure.
- Explicit `systemctl stop` suppresses automatic restart, even for the lidar `Restart=always` unit.
- These services detect process exits, **not an alive but stalled scan stream**. Check `/scan`.
- Reconnect handling relies on the driver exiting on device failure; if it stays alive/stalled,
  inspect logs and explicitly restart sensing after checking USB/power. No scan watchdog is claimed.
- SIGINT is sent to the service process group so ROS driver cleanup can run. After 15 seconds,
  systemd may force termination; software shutdown is not a safety-rated motor/lidar power cutoff.
- ROS files/logs go to `/var/lib/omni-lidar`; service logs also go to journald.
- Checkout/home files are read-only inside services; system paths are protected and no privilege
  escalation is allowed. These are limited hardening measures, not a security certification.

## Stop, restart, update, disable

```bash
sudo systemctl stop omni-lidar.service omni-ui.service
sudo systemctl restart omni-lidar.service omni-ui.service
sudo systemctl disable --now omni-lidar.service omni-ui.service
```

Run only the relevant command; these are separate operations, not a startup sequence.
**Stopping these processes cannot stop a move already executing on STM32.** Use physical motor
power isolation if movement is active or uncertain.

Before updating units or code, stop services explicitly and back up local robot config/mount files.
After updating/building, rerun installer with `--apply --enable`. It refuses rewriting active units.
Moving the checkout requires reinstalling units to update their absolute paths.

For manual hardware bench work, stop the boot UI first, then use the documented foreground
UART commands. The boot UI stays simulation-only; changing a config file cannot arm it.
Do not edit units to insert hardware flags before motor firmware safety work is complete.

## Rollback / removal

Disable and stop first. For an older unit definition, review its `.backup-TIMESTAMP` file in
`/etc/systemd/system`, restore the intended definition while stopped, then `sudo systemctl daemon-reload`.
Do not blindly restore an old unit that could arm motors.

To remove just these generated units after disabling:

```bash
sudo rm /etc/systemd/system/omni-lidar.service /etc/systemd/system/omni-ui.service
sudo systemctl daemon-reload
```

Backups and `/var/lib/omni-lidar` logs are retained. Do not delete unrelated units or logs.

## Remaining robot-specific inputs

Pi SSH address/account, installed native ARM environment, verified UART connector/routing,
measured lidar mount, and physical safety acceptance remain operator tasks.
See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) and [CONNECTION_VERIFICATION.md](CONNECTION_VERIFICATION.md).
