import argparse
from .app import create_app
from .controller import Controller


def main():
    parser = argparse.ArgumentParser(description="Omni Pi backend; simulation by default")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--port", help="Pi UART device, e.g. /dev/serial0")
    parser.add_argument("--enable-hardware-motion", action="store_true",
                        help="Operator opt-in only after firmware safety fixes and bench validation")
    parser.add_argument("--completion-timeout", type=float, default=120.0)
    parser.add_argument("--http-port", type=int, default=5000)
    args = parser.parse_args()
    if args.completion_timeout <= 0 or not args.completion_timeout < float("inf"):
        parser.error("completion timeout must be finite and positive")
    if args.live and not args.port:
        parser.error("--live requires --port")
    if args.enable_hardware_motion and not args.live:
        parser.error("--enable-hardware-motion requires --live")
    controller = Controller(port=args.port, live=args.live,
                            hardware_enabled=args.enable_hardware_motion,
                            completion_timeout=args.completion_timeout)
    controller.start()
    try:
        create_app(controller).run(host="127.0.0.1", port=args.http_port,
                                   debug=False, use_reloader=False)
    finally:
        controller.close()


if __name__ == "__main__":
    main()
