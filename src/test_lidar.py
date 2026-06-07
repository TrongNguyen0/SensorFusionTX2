import argparse
import time


def import_pyrplidar():
    try:
        from pyrplidar import PyRPlidar
        return PyRPlidar
    except ImportError:
        from PyRPlidar import PyRPlidar
        return PyRPlidar


def value_of(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def parse_args():
    parser = argparse.ArgumentParser(description="Minimal RPLidar A1 start_scan test")
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--motor-pwm", type=int, default=660)
    parser.add_argument("--warmup", type=float, default=2.0)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument(
        "--probe-info",
        action="store_true",
        help="Call get_info/get_health before scanning. Default is off because it can disturb some A1 units.",
    )
    parser.add_argument(
        "--dtr",
        choices=["none", "true", "false"],
        default="none",
        help="Optionally force serial DTR before scanning.",
    )
    return parser.parse_args()


def get_serial(lidar):
    candidates = [
        lidar,
        getattr(lidar, "lidar_serial", None),
        getattr(getattr(lidar, "lidar_serial", None), "_serial", None),
        getattr(getattr(lidar, "lidar_serial", None), "serial", None),
    ]

    for candidate in candidates:
        if candidate is not None and hasattr(candidate, "reset_input_buffer"):
            return candidate
    return None


def clear_serial_buffers(lidar):
    serial_port = get_serial(lidar)
    if serial_port is None:
        print("Serial buffer clear skipped: serial object not accessible")
        return

    if hasattr(serial_port, "reset_input_buffer"):
        serial_port.reset_input_buffer()
    if hasattr(serial_port, "reset_output_buffer"):
        serial_port.reset_output_buffer()
    print("Serial buffers cleared")


def set_dtr(lidar, dtr_mode):
    if dtr_mode == "none":
        return

    serial_port = get_serial(lidar)
    if serial_port is None or not hasattr(serial_port, "setDTR"):
        print("DTR skipped: serial object not accessible")
        return

    value = dtr_mode == "true"
    serial_port.setDTR(value)
    print("DTR forced to {}".format(value))


def get_scan_iterator(lidar):
    scan = lidar.start_scan()
    if callable(scan):
        return scan()
    return scan


def main():
    args = parse_args()
    PyRPlidar = import_pyrplidar()
    lidar = PyRPlidar()

    try:
        print("Connecting LiDAR on {}...".format(args.port))
        lidar.connect(port=args.port, baudrate=args.baudrate, timeout=args.timeout)
        clear_serial_buffers(lidar)
        set_dtr(lidar, args.dtr)
        time.sleep(0.2)

        if args.probe_info:
            try:
                print("Info:", lidar.get_info())
                print("Health:", lidar.get_health())
            except Exception as exc:
                print("Info/health warning:", exc)
            clear_serial_buffers(lidar)
            time.sleep(0.2)

        print("Starting motor PWM {}...".format(args.motor_pwm))
        lidar.set_motor_pwm(args.motor_pwm)
        time.sleep(args.warmup)
        clear_serial_buffers(lidar)
        time.sleep(0.2)

        print("Starting standard scan with start_scan()...")
        iterator = get_scan_iterator(lidar)

        printed = 0
        for measurement in iterator:
            angle = value_of(measurement, "angle")
            distance = value_of(measurement, "distance")
            quality = value_of(measurement, "quality")
            start_flag = value_of(measurement, "start_flag")

            print(
                "{:02d}: angle={} distance={} quality={} start_flag={}".format(
                    printed + 1, angle, distance, quality, start_flag
                )
            )

            printed += 1
            if printed >= args.count:
                break

        print("Done. If distance has values > 0, LiDAR scan data is valid.")

    finally:
        try:
            lidar.stop()
        except Exception:
            pass
        try:
            lidar.set_motor_pwm(0)
        except Exception:
            pass
        try:
            lidar.disconnect()
        except Exception:
            pass
        print("LiDAR disconnected.")


if __name__ == "__main__":
    main()
