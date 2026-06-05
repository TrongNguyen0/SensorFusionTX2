import logging
import time
from typing import Optional, Tuple

import numpy as np
import pyrealsense2 as rs


class RealSenseFrame(object):
    def __init__(self, color: np.ndarray, depth: np.ndarray, timestamp_ms: int) -> None:
        self.color = color
        self.depth = depth
        self.timestamp_ms = timestamp_ms


class RealSenseReader(object):
    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        timeout_ms: int = 5000,
        reconnect_delay: float = 2.0,
        max_reconnect_attempts: int = 3,
    ) -> None:
        self.width = width
        self.height = height
        self.fps = fps
        self.timeout_ms = timeout_ms
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        self.pipeline = None
        self.align = None
        self.running = False
        self.logger = logging.getLogger(self.__class__.__name__)

    def start(self) -> None:
        self.stop()
        self.logger.info(
            "Starting RealSense %dx%d @ %d FPS", self.width, self.height, self.fps
        )

        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.depth, self.width, self.height, rs.format.z16, self.fps)
        config.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps)
        pipeline.start(config)

        self.pipeline = pipeline
        self.align = rs.align(rs.stream.color)
        self.running = True

    def read(self) -> RealSenseFrame:
        if not self.running or self.pipeline is None or self.align is None:
            self.start()

        last_error = None
        attempts = max(1, self.max_reconnect_attempts)

        for attempt in range(1, attempts + 1):
            try:
                return self._read_once()
            except Exception as exc:
                last_error = exc
                self.logger.warning(
                    "RealSense read failed on attempt %d/%d: %s",
                    attempt,
                    attempts,
                    exc,
                )
                self._reconnect()

        raise RuntimeError("RealSense read failed: {}".format(last_error))

    def stop(self) -> None:
        if self.pipeline is not None:
            try:
                self.pipeline.stop()
            except Exception as exc:
                self.logger.debug("RealSense stop ignored: %s", exc)
        self.pipeline = None
        self.align = None
        self.running = False

    def _read_once(self) -> RealSenseFrame:
        frames = self.pipeline.wait_for_frames(timeout_ms=self.timeout_ms)
        aligned = self.align.process(frames)
        depth_frame = aligned.get_depth_frame()
        color_frame = aligned.get_color_frame()

        if not depth_frame or not color_frame:
            raise RuntimeError("RealSense returned missing color/depth frame")

        color = np.asanyarray(color_frame.get_data()).copy()
        depth = np.asanyarray(depth_frame.get_data()).copy()
        timestamp_ms = int(time.time() * 1000)
        return RealSenseFrame(color=color, depth=depth, timestamp_ms=timestamp_ms)

    def _reconnect(self) -> None:
        self.logger.info("Reconnecting RealSense after %.1fs", self.reconnect_delay)
        self.stop()
        time.sleep(self.reconnect_delay)
        self.start()

    def __enter__(self) -> "RealSenseReader":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
