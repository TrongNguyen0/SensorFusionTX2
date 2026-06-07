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
    parser = argparse.ArgumentParser(description="Standalone PyRPlidar diagnostic test")
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--motor-pwm", type=int, default=660)
    parser.add_argument("--warmup", type=float, default=3.0)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument(
        "--mode",
        choices=["standard", "force"],
        default="standard",
        help="standard uses start_scan(); force uses force_scan().",
    )
    parser.add_argument(
        "--probe-info",
        action="store_true",
        help="Call get_info/get_health before scan. Default is off.",
    )
    parser.add_argument(
        "--dtr",
        choices=["none", "true", "false"],
        default="none",
        help="Optionally force DTR after connect.",
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
        if candidate is not None and hasattr(candidate, "read"):
            return candidate
    return None


def clear_buffers(lidar):
    serial_port = get_serial(lidar)
    if serial_port is None:
        print("Serial object not accessible; skip buffer clear")
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
        print("Serial object has no setDTR; skip DTR")
        return

    value = dtr_mode == "true"
    serial_port.setDTR(value)
    print("DTR forced to {}".format(value))


def start_scan_iterator(lidar, mode):
    if mode == "standard":
        scan = lidar.start_scan()
    else:
        scan = lidar.force_scan()

    if callable(scan):
        return scan()
    return scan


def main():
    args = parse_args()
    PyRPlidar = import_pyrplidar()
    lidar = PyRPlidar()

    valid_count = 0
    total_count = 0

    try:
        print("Connecting LiDAR on {}...".format(args.port))
        lidar.connect(port=args.port, baudrate=args.baudrate, timeout=args.timeout)
        clear_buffers(lidar)
        set_dtr(lidar, args.dtr)
        time.sleep(0.2)

        if args.probe_info:
            try:
                print("Info:", lidar.get_info())
                print("Health:", lidar.get_health())
            except Exception as exc:
                print("Info/health warning:", exc)
            clear_buffers(lidar)
            time.sleep(0.2)

        print("Starting motor PWM {}...".format(args.motor_pwm))
        lidar.set_motor_pwm(args.motor_pwm)
        print("Warmup {:.1f}s...".format(args.warmup))
        time.sleep(args.warmup)
        clear_buffers(lidar)
        time.sleep(0.2)

        print("Starting scan mode: {}".format(args.mode))
        iterator = start_scan_iterator(lidar, args.mode)

        while total_count < args.count:
            measurement = next(iterator)
            total_count += 1

            angle = value_of(measurement, "angle")
            distance = value_of(measurement, "distance")
            quality = value_of(measurement, "quality")
            start_flag = value_of(measurement, "start_flag")

            try:
                distance_value = float(distance)
            except (TypeError, ValueError):
                distance_value = 0.0

            if distance_value > 0:
                valid_count += 1

            print(
                "{:03d}: angle={} distance={} quality={} start_flag={} valid={}".format(
                    total_count,
                    angle,
                    distance,
                    quality,
                    start_flag,
                    distance_value > 0,
                )
            )

        print("Summary: total={}, valid_distance_gt_0={}".format(total_count, valid_count))

    except Exception as exc:
        print("LiDAR diagnostic error:", exc)
        print("Summary before error: total={}, valid_distance_gt_0={}".format(total_count, valid_count))

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
