import argparse
import logging
import os
import time

import cv2

from calibration_loader import CalibrationLoader
from dataset_logger import DatasetLogger
from fusion_engine import FusionEngine
from fusion_visualizer import FusionVisualizer
from lidar_reader import LidarReader
from realsense_reader import RealSenseReader
from tcp_server import TcpFrameServer


def default_calibration_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "calibration_result_pnp.npz"))


def parse_args():
    parser = argparse.ArgumentParser(description="Realtime RealSense + RPLidar fusion")
    parser.add_argument("--calibration", default=default_calibration_path())
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--lidar-port", default="/dev/ttyUSB0")
    parser.add_argument("--lidar-baudrate", type=int, default=115200)
    parser.add_argument("--lidar-timeout", type=float, default=3.0)
    parser.add_argument("--scan-mode", choices=["force", "standard", "express"], default="force")
    parser.add_argument("--motor-pwm", type=int, default=660)
    parser.add_argument("--dataset-root", default="dataset")
    parser.add_argument("--tcp-host", default="0.0.0.0")
    parser.add_argument("--tcp-port", type=int, default=9999)
    parser.add_argument("--jpeg-quality", type=int, default=80)
    parser.add_argument("--no-display", action="store_true")
    parser.add_argument("--no-tcp", action="store_true")
    parser.add_argument("--min-distance-mm", type=float, default=50.0)
    parser.add_argument("--max-distance-mm", type=float, default=12000.0)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def update_fps(last_time: float, fps: float) -> (float, float):
    now = time.time()
    dt = max(now - last_time, 1e-6)
    instant = 1.0 / dt
    if fps <= 0:
        fps = instant
    else:
        fps = 0.9 * fps + 0.1 * instant
    return now, fps


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)
    logger = logging.getLogger("main")

    calibration = CalibrationLoader(args.calibration).load()
    fusion_engine = FusionEngine(
        calibration.K,
        calibration.R,
        calibration.T,
        image_width=args.width,
        image_height=args.height,
        min_distance_mm=args.min_distance_mm,
        max_distance_mm=args.max_distance_mm,
    )
    visualizer = FusionVisualizer()
    dataset_logger = DatasetLogger(args.dataset_root)

    camera = RealSenseReader(width=args.width, height=args.height, fps=args.fps)
    lidar = LidarReader(
        port=args.lidar_port,
        baudrate=args.lidar_baudrate,
        timeout=args.lidar_timeout,
        scan_mode=args.scan_mode,
        motor_pwm=args.motor_pwm,
    )
    tcp_server = None if args.no_tcp else TcpFrameServer(
        host=args.tcp_host,
        port=args.tcp_port,
        jpeg_quality=args.jpeg_quality,
    )

    frame_id = 0
    fps = 0.0
    last_frame_time = time.time()

    try:
        camera.start()
        lidar.start()
        if tcp_server is not None:
            tcp_server.start()

        logger.info("Realtime fusion started. Press S to save, Q/Esc to quit.")

        while True:
            frame = camera.read()
            lidar_scan = lidar.get_scan()

            fusion = fusion_engine.project_lidar(lidar_scan)
            last_frame_time, fps = update_fps(last_frame_time, fps)
            fusion_frame = visualizer.create_frame(
                frame.color,
                frame.depth,
                fusion.image_points,
                frame_id=frame_id,
                fps=fps,
            )

            if tcp_server is not None:
                tcp_server.send_frame(fusion_frame)

            key = -1
            if not args.no_display:
                cv2.imshow("Sensor Fusion", fusion_frame)
                key = cv2.waitKey(1) & 0xFF

            if key in (ord("s"), ord("S")):
                saved_dir = dataset_logger.save(
                    color_image=frame.color,
                    depth_image=frame.depth,
                    fusion_image=fusion_frame,
                    lidar_points=lidar_scan,
                    frame_id=frame_id,
                    metadata={
                        "projected_points": int(len(fusion.image_points)),
                        "camera_points": int(len(fusion.camera_points)),
                        "fps": float(fps),
                        "source_timestamp_ms": int(frame.timestamp_ms),
                    },
                )
                logger.info("Saved dataset sample: %s", saved_dir)

            if key in (ord("q"), ord("Q"), 27):
                break

            frame_id += 1

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        logger.info("Shutting down")
        if tcp_server is not None:
            tcp_server.stop()
        lidar.stop()
        camera.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
