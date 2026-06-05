import logging
import threading
import time
from typing import List, NamedTuple, Optional


class LidarPoint(NamedTuple):
    angle: float
    distance: float
    quality: int


class LidarReader(object):
    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 115200,
        timeout: float = 3.0,
        scan_mode: str = "force",
        motor_pwm: int = 660,
        min_scan_points: int = 5,
        reconnect_delay: float = 2.0,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.scan_mode = scan_mode
        self.motor_pwm = motor_pwm
        self.min_scan_points = min_scan_points
        self.reconnect_delay = reconnect_delay

        self._lidar = None
        self._thread = None
        self._lock = threading.Lock()
        self._running = False
        self._latest_scan = []  # type: List[LidarPoint]
        self._last_error = None  # type: Optional[Exception]
        self.logger = logging.getLogger(self.__class__.__name__)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker)
        self._thread.daemon = True
        self._thread.start()
        self.logger.info("LiDAR reader thread started")

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        self._disconnect()

    def get_scan(self) -> List[LidarPoint]:
        with self._lock:
            return list(self._latest_scan)

    def get_last_error(self) -> Optional[Exception]:
        with self._lock:
            return self._last_error

    def _worker(self) -> None:
        while self._running:
            try:
                self._connect()
                self._read_loop()
            except Exception as exc:
                with self._lock:
                    self._last_error = exc
                self.logger.exception("LiDAR read loop failed: %s", exc)
                self._disconnect()
                if self._running:
                    time.sleep(self.reconnect_delay)

    def _connect(self) -> None:
        PyRPlidar = self._import_pyrplidar()
        self._disconnect()

        lidar = PyRPlidar()
        self.logger.info("Connecting LiDAR on %s at %d baud", self.port, self.baudrate)
        lidar.connect(port=self.port, baudrate=self.baudrate, timeout=self.timeout)

        try:
            self.logger.info("LiDAR info: %s", lidar.get_info())
            self.logger.info("LiDAR health: %s", lidar.get_health())
        except Exception as exc:
            self.logger.warning("LiDAR info/health warning: %s", exc)

        if self.motor_pwm > 0:
            lidar.set_motor_pwm(self.motor_pwm)
            time.sleep(2.0)

        self._clear_buffers(lidar)
        self._lidar = lidar

    def _read_loop(self) -> None:
        iterator = self._get_iterator(self._lidar)
        current_scan = []  # type: List[LidarPoint]

        while self._running:
            measurement = next(iterator)
            point = self._parse_measurement(measurement)
            if point is None:
                continue

            start_flag = self._get_value(measurement, "start_flag", False)
            if start_flag and len(current_scan) >= self.min_scan_points:
                with self._lock:
                    self._latest_scan = current_scan
                    self._last_error = None
                current_scan = []

            current_scan.append(point)

            if len(current_scan) > 5000:
                self.logger.warning("LiDAR scan buffer too large; resetting current scan")
                current_scan = []

    def _get_iterator(self, lidar):
        if self.scan_mode == "force":
            scan = lidar.force_scan()
        elif self.scan_mode == "standard":
            scan = lidar.start_scan()
        elif self.scan_mode == "express":
            scan = lidar.start_scan_express(0)
        else:
            raise ValueError("Unsupported scan_mode: {}".format(self.scan_mode))

        if callable(scan):
            return scan()
        return scan

    def _parse_measurement(self, measurement) -> Optional[LidarPoint]:
        angle = self._get_value(measurement, "angle", None)
        distance = self._get_value(measurement, "distance", None)
        quality = self._get_value(measurement, "quality", 0)

        if angle is None or distance is None:
            return None

        try:
            return LidarPoint(angle=float(angle), distance=float(distance), quality=int(quality))
        except (TypeError, ValueError):
            return None

    def _disconnect(self) -> None:
        lidar = self._lidar
        self._lidar = None
        if lidar is None:
            return

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

    @staticmethod
    def _clear_buffers(lidar) -> None:
        serial_obj = LidarReader._get_serial(lidar)
        if serial_obj is None:
            return
        try:
            if hasattr(serial_obj, "reset_input_buffer"):
                serial_obj.reset_input_buffer()
            if hasattr(serial_obj, "reset_output_buffer"):
                serial_obj.reset_output_buffer()
        except Exception:
            pass

    @staticmethod
    def _get_serial(lidar):
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

    @staticmethod
    def _get_value(obj, name: str, default):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    @staticmethod
    def _import_pyrplidar():
        try:
            from pyrplidar import PyRPlidar
            return PyRPlidar
        except ImportError:
            from PyRPlidar import PyRPlidar
            return PyRPlidar

    def __enter__(self) -> "LidarReader":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
