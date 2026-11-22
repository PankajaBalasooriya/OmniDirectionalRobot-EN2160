"""Single-owner adapter for the existing, unframed two-byte UART protocol."""
import threading
import time


COMMANDS = {
    "forward": 0x01, "backward": 0x02, "left": 0x03, "right": 0x04,
    "forward_left": 0x05, "forward_right": 0x06, "backward_left": 0x07,
    "backward_right": 0x08, "rotate_cw": 0x09, "rotate_ccw": 0x0A,
}
TELEMETRY = {0xA1: "motion_completed", 0xA2: "x_distance_raw",
             0xA3: "y_distance_raw", 0xA4: "current_raw",
             0xA5: "encoder_raw", 0xA6: "system_status_raw"}


class Unavailable(Exception):
    pass


class Busy(Exception):
    pass


class Controller:
    def __init__(self, *, port=None, baudrate=115200, live=False,
                 hardware_enabled=False, completion_timeout=120.0,
                 serial_factory=None):
        self.live = live
        self.port = port
        self.baudrate = baudrate
        self.hardware_enabled = hardware_enabled
        self.completion_timeout = completion_timeout
        self.serial_factory = serial_factory
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.closing = threading.Event()
        self.thread = None
        self.pending = None
        self.state = "idle" if not live else "disconnected"
        self.error = None
        self.telemetry = {}
        self.last_command = None

    def start(self):
        with self.lock:
            if self.closing.is_set():
                raise RuntimeError("Cannot start a closed controller")
            if not self.live:
                return
            if self.thread is not None:
                raise RuntimeError("Controller already started")
            if not self.port:
                raise ValueError("Live mode requires --port")
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def snapshot(self):
        with self.lock:
            return {"mode": "uart" if self.live else "simulation",
                    "state": self.state, "port": self.port,
                    "baudrate": self.baudrate, "error": self.error,
                    "hardware_enabled": self.hardware_enabled,
                    "last_command": self.last_command,
                    "telemetry": dict(self.telemetry),
                    "stop_supported": False}

    def move(self, direction, value):
        if direction not in COMMANDS:
            raise ValueError("Unknown direction")
        if type(value) is not int or not 1 <= value <= 255:
            raise ValueError("value must be an integer from 1 to 255 (raw firmware units)")
        packet = bytes((COMMANDS[direction], value))
        with self.lock:
            if self.closing.is_set():
                raise Unavailable("Backend is shutting down")
            if self.live and not self.hardware_enabled:
                raise Unavailable("Hardware motion is disabled; see firmware safety requirements")
            if self.state in {"disconnected", "fault"}:
                raise Unavailable(self.error or self.state)
            if self.state != "idle":
                raise Busy("A motion is already pending; commands are not queued")
            self.last_command = {"direction": direction, "value": value,
                                 "packet_hex": packet.hex()}
            if not self.live:
                return {"accepted": True, "simulated": True, "packet_hex": packet.hex()}
            self.pending = packet
            self.state = "pending"
        self.wake.set()
        return {"accepted": True, "simulated": False, "packet_hex": packet.hex()}

    def _run(self):
        connection = None
        try:
            factory = self.serial_factory
            if factory is None:
                from serial import Serial
                factory = Serial
            connection = factory(self.port, self.baudrate, timeout=0.05, write_timeout=1)
            connection.reset_input_buffer()
            with self.lock:
                self.state = "idle"
            buffer = bytearray()
            deadline = None
            while not self.closing.is_set():
                with self.lock:
                    packet = self.pending
                    self.pending = None
                if packet is not None:
                    # No retransmission: replay could execute the same physical move twice.
                    connection.reset_input_buffer()
                    buffer.clear()
                    with self.lock:
                        if self.closing.is_set():
                            break
                        if connection.write(packet) != len(packet):
                            raise OSError("Partial UART write; motion outcome is unknown")
                        deadline = time.monotonic() + self.completion_timeout
                        self.state = "awaiting_completion"
                chunk = connection.read(2 - len(buffer))
                buffer.extend(chunk)
                if len(buffer) == 2:
                    kind, value = buffer
                    buffer.clear()
                    if kind not in TELEMETRY:
                        raise OSError("Unknown telemetry ID; UART alignment is uncertain")
                    with self.lock:
                        self.telemetry[TELEMETRY[kind]] = value
                        if kind == 0xA1 and deadline is not None:
                            if value != 1:
                                raise OSError("Unexpected completion value")
                            # Firmware-reported completion is not proof of physical standstill.
                            self.state = "idle"
                            deadline = None
                if deadline is not None and time.monotonic() >= deadline:
                    raise TimeoutError("No completion received; robot may still be moving")
                if not chunk:
                    self.wake.wait(0.01)
                    self.wake.clear()
        except Exception as exc:
            with self.lock:
                self.state = "fault"
                self.error = str(exc)
                self.pending = None
        finally:
            if connection is not None:
                connection.close()

    def close(self):
        # Closing UART cannot stop this firmware. Never claim otherwise.
        with self.lock:
            self.closing.set()
            self.pending = None
        self.wake.set()
        if self.thread is not None:
            self.thread.join(timeout=2)
