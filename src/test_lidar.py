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
    return parser.parse_args()


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

        try:
            print("Info:", lidar.get_info())
            print("Health:", lidar.get_health())
        except Exception as exc:
            print("Info/health warning:", exc)

        print("Starting motor PWM {}...".format(args.motor_pwm))
        lidar.set_motor_pwm(args.motor_pwm)
        time.sleep(args.warmup)

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
