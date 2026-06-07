import argparse
import os
import time

import cv2
import numpy as np
import pyrealsense2 as rs


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
    parser = argparse.ArgumentParser(description="Minimal RealSense + RPLidar fusion")
    parser.add_argument("--calibration", default="calibration_result_pnp.npz")
    parser.add_argument("--lidar-port", default="/dev/ttyUSB0")
    parser.add_argument("--lidar-baudrate", type=int, default=115200)
    parser.add_argument("--lidar-timeout", type=float, default=3.0)
    parser.add_argument("--motor-pwm", type=int, default=660)
    parser.add_argument("--warmup", type=float, default=2.0)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--lidar-samples-per-frame", type=int, default=720)
    parser.add_argument("--max-draw-points", type=int, default=600)
    parser.add_argument("--min-distance", type=float, default=50.0)
    parser.add_argument("--max-distance", type=float, default=12000.0)
    return parser.parse_args()


def load_calibration(path):
    if not os.path.exists(path):
        raise IOError("Calibration file not found: {}".format(path))

    data = np.load(path)
    K = np.asarray(data["K"], dtype=np.float64)
    R = np.asarray(data["R"], dtype=np.float64)
    T = np.asarray(data["T"], dtype=np.float64)

    if K.shape != (3, 3):
        raise ValueError("K shape must be (3,3), got {}".format(K.shape))
    if R.shape != (3, 3):
        raise ValueError("R shape must be (3,3), got {}".format(R.shape))
    if T.shape == (3,):
        T = T.reshape(3, 1)
    if T.shape != (3, 1):
        raise ValueError("T shape must be (3,1), got {}".format(T.shape))

    print("Calibration loaded.")
    return K, R, T


def start_realsense(width, height, fps):
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)
    config.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)
    print("Starting RealSense {}x{} @ {} FPS".format(width, height, fps))
    pipeline.start(config)
    align = rs.align(rs.stream.color)
    return pipeline, align


def read_realsense_frame(pipeline, align):
    frames = pipeline.wait_for_frames()
    aligned = align.process(frames)
    depth_frame = aligned.get_depth_frame()
    color_frame = aligned.get_color_frame()

    if not depth_frame or not color_frame:
        return None, None

    color = np.asanyarray(color_frame.get_data()).copy()
    depth = np.asanyarray(depth_frame.get_data()).copy()
    return color, depth


def start_lidar(port, baudrate, timeout, motor_pwm, warmup):
    PyRPlidar = import_pyrplidar()
    lidar = PyRPlidar()

    print("Connecting LiDAR on {}...".format(port))
    lidar.connect(port=port, baudrate=baudrate, timeout=timeout)

    try:
        print("LiDAR info:", lidar.get_info())
        print("LiDAR health:", lidar.get_health())
    except Exception as exc:
        print("LiDAR info/health warning:", exc)

    print("Starting LiDAR motor PWM {}...".format(motor_pwm))
    lidar.set_motor_pwm(motor_pwm)
    time.sleep(warmup)

    print("Starting LiDAR standard scan with start_scan()...")
    scan = lidar.start_scan()
    iterator = scan() if callable(scan) else scan
    return lidar, iterator


def stop_lidar(lidar):
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
    print("LiDAR stopped.")


def read_lidar_points(iterator, sample_count, min_distance, max_distance):
    points = []

    while len(points) < sample_count:
        measurement = next(iterator)
        angle = value_of(measurement, "angle")
        distance = value_of(measurement, "distance")
        quality = value_of(measurement, "quality", 0)

        if angle is None or distance is None:
            continue

        try:
            angle = float(angle)
            distance = float(distance)
            quality = int(quality)
        except (TypeError, ValueError):
            continue

        if distance <= min_distance or distance >= max_distance:
            continue

        points.append((angle, distance, quality))

    return points


def lidar_to_xyz(lidar_points):
    if not lidar_points:
        return np.empty((0, 3), dtype=np.float64)

    xyz = []
    for angle, distance, _quality in lidar_points:
        rad = np.deg2rad(angle)
        x = distance * np.sin(rad)
        y = 0.0
        z = distance * np.cos(rad)
        xyz.append((x, y, z))

    return np.asarray(xyz, dtype=np.float64)


def project_lidar_points(lidar_points, K, R, T, image_width, image_height):
    lidar_xyz = lidar_to_xyz(lidar_points)
    if lidar_xyz.shape[0] == 0:
        return np.empty((0, 2), dtype=np.int32)

    camera_xyz = (R.dot(lidar_xyz.T) + T).T
    z = camera_xyz[:, 2]
    valid_z = z > 0.0
    camera_xyz = camera_xyz[valid_z]

    if camera_xyz.shape[0] == 0:
        return np.empty((0, 2), dtype=np.int32)

    uvw = K.dot(camera_xyz.T).T
    u = uvw[:, 0] / uvw[:, 2]
    v = uvw[:, 1] / uvw[:, 2]

    valid_uv = (
        (u >= 0)
        & (u < image_width)
        & (v >= 0)
        & (v < image_height)
        & np.isfinite(u)
        & np.isfinite(v)
    )

    if not np.any(valid_uv):
        return np.empty((0, 2), dtype=np.int32)

    return np.stack((u[valid_uv], v[valid_uv]), axis=1).astype(np.int32)


def draw_points(image, points, max_draw_points):
    if len(points) == 0:
        return

    if len(points) > max_draw_points:
        indices = np.linspace(0, len(points) - 1, max_draw_points).astype(np.int32)
        points = points[indices]

    for u, v in points:
        cv2.circle(image, (int(u), int(v)), 3, (0, 255, 0), -1)


def make_display(color, depth, projected_points, fps, frame_count, lidar_count, max_draw_points):
    fusion = color.copy()
    draw_points(fusion, projected_points, max_draw_points)

    text = "FPS: {:.1f} | Frame: {} | LiDAR valid: {} | Projected: {}".format(
        fps,
        frame_count,
        lidar_count,
        len(projected_points),
    )
    cv2.rectangle(fusion, (8, 8), (620, 42), (0, 0, 0), -1)
    cv2.putText(
        fusion,
        text,
        (15, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    depth_vis = cv2.applyColorMap(
        cv2.convertScaleAbs(depth, alpha=0.03),
        cv2.COLORMAP_JET,
    )

    return np.vstack((fusion, depth_vis))


def main():
    args = parse_args()
    K, R, T = load_calibration(args.calibration)

    pipeline = None
    lidar = None

    frame_count = 0
    fps = 0.0
    last_time = time.time()

    try:
        pipeline, align = start_realsense(args.width, args.height, args.fps)
        lidar, lidar_iterator = start_lidar(
            args.lidar_port,
            args.lidar_baudrate,
            args.lidar_timeout,
            args.motor_pwm,
            args.warmup,
        )

        while True:
            color, depth = read_realsense_frame(pipeline, align)
            if color is None or depth is None:
                continue

            lidar_points = read_lidar_points(
                lidar_iterator,
                args.lidar_samples_per_frame,
                args.min_distance,
                args.max_distance,
            )

            projected = project_lidar_points(
                lidar_points,
                K,
                R,
                T,
                args.width,
                args.height,
            )

            now = time.time()
            dt = max(now - last_time, 1e-6)
            last_time = now
            instant_fps = 1.0 / dt
            fps = instant_fps if fps == 0.0 else 0.9 * fps + 0.1 * instant_fps
            frame_count += 1

            display = make_display(
                color,
                depth,
                projected,
                fps,
                frame_count,
                len(lidar_points),
                args.max_draw_points,
            )

            cv2.imshow("RealSense + RPLidar Fusion", display)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break

    finally:
        if pipeline is not None:
            pipeline.stop()
            print("RealSense stopped.")
        stop_lidar(lidar)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
