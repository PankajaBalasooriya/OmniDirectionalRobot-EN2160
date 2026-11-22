import queue
import threading
import unittest

from pi_backend.app import create_app
from pi_backend.controller import Busy, Controller, Unavailable


class FakeSerial:
    def __init__(self, *args, **kwargs):
        self.incoming = queue.Queue()
        self.written = queue.Queue()
        self.closed = False

    def reset_input_buffer(self):
        while not self.incoming.empty():
            self.incoming.get_nowait()

    def write(self, packet):
        self.written.put(packet)
        return len(packet)

    def read(self, size):
        try:
            return self.incoming.get(timeout=0.01)
        except queue.Empty:
            return b""

    def close(self):
        self.closed = True


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.controller = Controller()
        self.client = create_app(self.controller).test_client()
        self.bind_client(self.client)

    def bind_client(self, client):
        status = client.get("/api/status").json
        client.environ_base.update(HTTP_X_BACKEND_ID=status["backend_id"],
                                   HTTP_X_EXPECTED_MODE=status["mode"])

    def test_restarted_backend_rejects_stale_page(self):
        stale = self.client.get("/api/status").json
        live = Controller(live=True, port="fake", hardware_enabled=True)
        client = create_app(live).test_client()
        response = client.post("/api/move", json={"direction": "forward", "value": 1},
                               headers={"X-Backend-ID": stale["backend_id"],
                                        "X-Expected-Mode": stale["mode"]})
        self.assertEqual(response.status_code, 409)
        self.assertIsNone(live.pending)
        # Even with the current instance token, an incorrect mode is rejected.
        current = client.get("/api/status").json
        response = client.post("/api/move", json={"direction": "forward", "value": 1},
                               headers={"X-Backend-ID": current["backend_id"],
                                        "X-Expected-Mode": "simulation"})
        self.assertEqual(response.status_code, 409)

    def test_browser_ui_and_assets(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/html")
        for asset, mimetype in [("control.js", "javascript"), ("style.css", "text/css")]:
            with self.subTest(asset=asset):
                response = self.client.get("/static/" + asset)
                self.assertEqual(response.status_code, 200)
                self.assertIn(mimetype, response.mimetype)
                response.close()

    def test_ui_cannot_bypass_hardware_interlock(self):
        controller = Controller(live=True, port="fake")
        client = create_app(controller).test_client()
        self.bind_client(client)
        self.assertEqual(client.get("/").status_code, 200)
        self.assertEqual(client.post("/api/move", json={
            "direction": "forward", "value": 1}).status_code, 503)

    def test_simulation_encodes_existing_protocol(self):
        response = self.client.post("/api/move", json={"direction": "forward", "value": 12})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json["packet_hex"], "010c")
        self.assertTrue(response.json["simulated"])
        self.assertEqual(self.client.get("/api/status").json["state"], "idle")

    def test_validation(self):
        for value in [0, 256, -1, True, 1.5, "2", None]:
            with self.subTest(value=value):
                self.assertEqual(self.client.post("/api/move", json={
                    "direction": "forward", "value": value}).status_code, 400)
        for body in [{}, [], {"direction": [], "value": 1},
                     {"direction": "stop", "value": 1},
                     {"direction": "forward", "value": 1, "extra": 2}]:
            self.assertEqual(self.client.post("/api/move", json=body).status_code, 400)

    def test_no_fake_stop(self):
        self.assertEqual(self.client.post("/api/stop").status_code, 501)

    def test_hardware_interlock(self):
        controller = Controller(live=True, port="fake")
        with self.assertRaises(Unavailable):
            controller.move("forward", 1)

    def test_shutdown_rejects_commands(self):
        self.controller.close()
        self.assertEqual(self.client.post("/api/move", json={
            "direction": "forward", "value": 1}).status_code, 503)

    def make_live(self, timeout=1):
        fake = FakeSerial()
        ready = threading.Event()
        def factory(*args, **kwargs):
            ready.set()
            return fake
        controller = Controller(live=True, port="fake", hardware_enabled=True,
                                serial_factory=factory, completion_timeout=timeout)
        controller.start()
        self.addCleanup(controller.close)
        self.assertTrue(ready.wait(1))
        # Snapshot takes the same lock as worker state publication.
        self.wait_state(controller, "idle")
        return controller, fake

    def wait_state(self, controller, expected):
        import time
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            if controller.snapshot()["state"] == expected:
                return
            threading.Event().wait(0.005)
        self.fail(controller.snapshot())

    def test_single_outstanding_and_fragmented_telemetry(self):
        controller, fake = self.make_live()
        controller.move("right", 7)
        self.assertEqual(fake.written.get(timeout=1), b"\x04\x07")
        with self.assertRaises(Busy):
            controller.move("forward", 1)
        for byte in [b"\xa2", b"\x0a", b"\xa1", b"\x01"]:
            fake.incoming.put(byte)
        self.wait_state(controller, "idle")
        self.assertEqual(controller.snapshot()["telemetry"]["x_distance_raw"], 10)

    def test_timeout_latches_fault_without_retry(self):
        controller, fake = self.make_live(timeout=0.02)
        controller.move("forward", 1)
        self.assertEqual(fake.written.get(timeout=1), b"\x01\x01")
        self.wait_state(controller, "fault")
        self.assertTrue(fake.written.empty())
        with self.assertRaises(Unavailable):
            controller.move("forward", 1)

    def test_start_only_once(self):
        controller, fake = self.make_live()
        with self.assertRaises(RuntimeError):
            controller.start()
        controller.close()
        with self.assertRaises(RuntimeError):
            controller.start()

    def test_shutdown_cancels_unsent_move(self):
        controller, fake = self.make_live()
        entered = threading.Event()
        release = threading.Event()
        original_reset = fake.reset_input_buffer
        def gated_reset():
            entered.set()
            release.wait(1)
            original_reset()
        fake.reset_input_buffer = gated_reset
        controller.move("forward", 1)
        self.assertTrue(entered.wait(1))
        closer = threading.Thread(target=controller.close)
        closer.start()
        self.assertTrue(controller.closing.wait(1))
        release.set()
        closer.join(1)
        self.assertFalse(closer.is_alive())
        self.assertTrue(fake.written.empty())
        self.assertTrue(fake.closed)

    def test_unknown_telemetry_faults(self):
        controller, fake = self.make_live()
        fake.incoming.put(b"\xff\x00")
        self.wait_state(controller, "fault")


if __name__ == "__main__":
    unittest.main()
