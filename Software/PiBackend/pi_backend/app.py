from uuid import uuid4

from flask import Flask, jsonify, render_template, request
from .controller import Busy, COMMANDS, Unavailable


def create_app(controller):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 4096
    backend_id = str(uuid4())
    mode = "uart" if controller.live else "simulation"

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/status")
    def status():
        return jsonify({**controller.snapshot(), "backend_id": backend_id})

    @app.get("/api/commands")
    def commands():
        return jsonify(directions=list(COMMANDS), value_range=[1, 255],
                       units="raw firmware units; not calibrated distance or angle",
                       stop_supported=False)

    @app.post("/api/move")
    def move():
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or set(data) != {"direction", "value"}:
            return jsonify(error="Expected exactly direction and value"), 400
        if not isinstance(data["direction"], str):
            return jsonify(error="direction must be a string"), 400
        if (request.headers.get("X-Backend-ID") != backend_id
                or request.headers.get("X-Expected-Mode") != mode):
            return jsonify(error="Backend instance or mode changed; refresh and verify safety"), 409
        try:
            result = controller.move(data["direction"], data["value"])
            return jsonify(result), 202
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        except Busy as exc:
            return jsonify(error=str(exc)), 409
        except Unavailable as exc:
            return jsonify(error=str(exc)), 503

    @app.post("/api/stop")
    def stop():
        return jsonify(error="Existing motor firmware has no UART STOP command. "
                       "Use the physical emergency stop; closing UART does not stop motion.",
                       stop_supported=False), 501

    return app
