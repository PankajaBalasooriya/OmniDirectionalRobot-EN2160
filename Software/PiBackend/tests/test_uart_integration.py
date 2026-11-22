"""HTTP -> backend -> actual pyserial -> virtual UART -> telemetry round trip.

Only a pseudo-terminal is used. No physical serial device is opened.
"""
import json
import os
import select
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from werkzeug.serving import make_server
from pi_backend.app import create_app
from pi_backend.controller import Controller


@unittest.skipUnless(os.name == "posix", "Pseudo-terminal test requires POSIX")
class UARTIntegrationTests(unittest.TestCase):
    def wait_for(self, predicate):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if predicate():
                return
            threading.Event().wait(0.005)
        self.fail("Timed out waiting for virtual UART state")

    def setUp(self):
        import pty
        self.master, self.slave = pty.openpty()
        self.addCleanup(os.close, self.master)
        self.addCleanup(os.close, self.slave)
        self.controller = Controller(port=os.ttyname(self.slave), live=True,
                                     hardware_enabled=True, completion_timeout=2)
        self.controller.start()
        self.addCleanup(self.controller.close)
        self.wait_for(lambda: self.controller.snapshot()["state"] == "idle")
        self.server = make_server("127.0.0.1", 0, create_app(self.controller), threaded=True)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.addCleanup(self.stop_server)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        _, status = self.request("/api/status")
        self.headers = {"X-Backend-ID": status["backend_id"], "X-Expected-Mode": "uart"}

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(2)

    def request(self, path, payload=None):
        headers = getattr(self, "headers", {}).copy()
        data = None
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        req = Request(self.url + path, data=data, headers=headers)
        try:
            with urlopen(req, timeout=2) as response:
                return response.status, json.load(response)
        except HTTPError as exc:
            with exc:
                return exc.code, json.load(exc)

    def read_command(self):
        data = b""
        deadline = time.monotonic() + 2
        while len(data) < 2:
            remaining = deadline - time.monotonic()
            self.assertGreater(remaining, 0)
            readable, _, _ = select.select([self.master], [], [], remaining)
            self.assertTrue(readable)
            data += os.read(self.master, 2 - len(data))
        return data

    def test_http_serial_roundtrip_all_commands(self):
        # Explicit expected firmware IDs, independent of the backend's table.
        directions = ["forward", "backward", "left", "right", "forward_left",
                      "forward_right", "backward_left", "backward_right",
                      "rotate_cw", "rotate_ccw"]
        for command_id, direction in enumerate(directions, 1):
            with self.subTest(direction=direction):
                code, body = self.request("/api/move", {"direction": direction, "value": 7})
                self.assertEqual(code, 202)
                self.assertFalse(body["simulated"])
                self.assertEqual(self.read_command(), bytes((command_id, 7)))
                code, _ = self.request("/api/move", {"direction": "forward", "value": 1})
                self.assertEqual(code, 409)
                os.write(self.master, b"\xa2\x19\xa3\x0a\xa1")
                os.write(self.master, b"\x01")
                self.wait_for(lambda: self.controller.snapshot()["state"] == "idle")
                code, status = self.request("/api/status")
                self.assertEqual(code, 200)
                self.assertEqual(status["telemetry"]["x_distance_raw"], 25)
                self.assertEqual(status["telemetry"]["y_distance_raw"], 10)
        # No wire-level STOP is invented.
        code, _ = self.request("/api/stop", {})
        self.assertEqual(code, 501)
        self.assertFalse(select.select([self.master], [], [], 0.05)[0])


if __name__ == "__main__":
    unittest.main()
