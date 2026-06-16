import json
import math
import os
import time

import cv2
import numpy as np
import pyrealsense2 as rs
from rplidar import RPLidar


# ==============================
# CONFIG
# ==============================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALIB_FILE = os.path.join(PROJECT_ROOT, "calibration_result_pnp.npz")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "fusion_output")
PORT = "COM3"

COLOR_WIDTH = 640
COLOR_HEIGHT = 480
DEPTH_WIDTH = 640
DEPTH_HEIGHT = 480
CAMERA_FPS = 30
FRONT_ANGLE_MIN = -90
FRONT_ANGLE_MAX = 90
MAX_DEPTH_MM = 6000


def ensure_output_dirs():
    for name in ["rgb", "depth_dense", "depth_sparse", "fusion", "metrics"]:
        os.makedirs(os.path.join(OUTPUT_DIR, name), exist_ok=True)


# ==============================
# CALIBRATION
# ==============================
def load_calibration():
    if not os.path.exists(CALIB_FILE):
        raise FileNotFoundError(f"Calibration file not found: {CALIB_FILE}")

    data = np.load(CALIB_FILE)
    K = data["K"]
    R = data["R"]
    T = data["T"].reshape(3, 1)

    if "distCoeffs" in data:
        dist_coeffs = data["distCoeffs"].reshape(-1, 1)
    else:
        dist_coeffs = np.zeros((5, 1), dtype=np.float64)
        print("Warning: distCoeffs not found in calibration file. Using zeros for backward compatibility.")

    if "rvec" in data:
        rvec = data["rvec"].reshape(3, 1)
    else:
        rvec, _ = cv2.Rodrigues(R)

    if "tvec" in data:
        tvec = data["tvec"].reshape(3, 1)
    else:
        tvec = T

    print("Loaded calibration")
    print("K:\n", K)
    print("T:\n", T.flatten())

    return K, dist_coeffs, R, T, rvec, tvec


# ==============================
# DEVICE INIT
# ==============================
def init_realsense():
    print("Initializing RealSense Camera...")
    ctx = rs.context()
    devices = ctx.query_devices()
    if len(devices) == 0:
        raise RuntimeError(
            "No RealSense device connected. Check USB cable/port, close apps using the camera, "
            "then reconnect the device."
        )

    device = devices[0]
    try:
        name = device.get_info(rs.camera_info.name)
        serial = device.get_info(rs.camera_info.serial_number)
        print(f"RealSense Device: {name} (S/N: {serial})")
    except Exception:
        print("RealSense device detected.")

    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, DEPTH_WIDTH, DEPTH_HEIGHT, rs.format.z16, CAMERA_FPS)
    config.enable_stream(rs.stream.color, COLOR_WIDTH, COLOR_HEIGHT, rs.format.bgr8, CAMERA_FPS)

    profile = pipeline.start(config)
    depth_sensor = profile.get_device().first_depth_sensor()
    depth_scale = depth_sensor.get_depth_scale()
    align = rs.align(rs.stream.color)

    print(f"RealSense depth scale: {depth_scale} meters/unit")
    return pipeline, align, depth_scale


def init_lidar():
    print("Initializing LIDAR...")
    lidar = RPLidar(PORT, baudrate=115200, timeout=3)
    print(f"LIDAR Info: {lidar.get_info()}")
    print(f"LIDAR Health: {lidar.get_health()}")
    return lidar


# ==============================
# GEOMETRY
# ==============================
def normalize_angle(angle):
    if angle > 180:
        return angle - 360
    return angle


def polar_to_cartesian(angle_deg, dist_mm):
    angle_rad = math.radians(angle_deg)
    x = dist_mm * math.sin(angle_rad)
    z = dist_mm * math.cos(angle_rad)
    return x, z


def scan_to_lidar_points(scan):
    points = []
    raw_count = 0
    front_count = 0

    for _, angle, dist in scan:
        raw_count += 1
        if dist <= 0:
            continue

        angle = normalize_angle(angle)
        if not (FRONT_ANGLE_MIN <= angle <= FRONT_ANGLE_MAX):
            continue

        x, z = polar_to_cartesian(angle, dist)
        points.append([x, 0.0, z])
        front_count += 1

    if len(points) == 0:
        return np.empty((0, 3), dtype=np.float64), raw_count, front_count

    return np.array(points, dtype=np.float64), raw_count, front_count


def project_lidar_points(lidar_points, K, dist_coeffs, R, T, rvec, tvec):
    if len(lidar_points) == 0:
        return np.empty((0, 2)), np.empty((0,))

    camera_points = (R @ lidar_points.T + T).T
    z_camera_mm = camera_points[:, 2]

    projected, _ = cv2.projectPoints(lidar_points, rvec, tvec, K, dist_coeffs)
    projected = projected.reshape(-1, 2)

    return projected, z_camera_mm


# ==============================
# VALIDATION
# ==============================
def summarize(values):
    if len(values) == 0:
        return {
            "mean": None,
            "median": None,
            "max": None,
            "std": None,
        }
    return {
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "max": float(np.max(values)),
        "std": float(np.std(values)),
    }


def render_sparse_depth(sparse_depth):
    clipped = np.clip(sparse_depth.astype(np.float32), 0, MAX_DEPTH_MM)
    depth_8u = cv2.convertScaleAbs(clipped, alpha=255.0 / MAX_DEPTH_MM)
    depth_cm = cv2.applyColorMap(depth_8u, cv2.COLORMAP_JET)
    depth_cm[sparse_depth == 0] = (0, 0, 0)
    return depth_cm


def make_metrics_panel(metrics, width=COLOR_WIDTH, height=COLOR_HEIGHT):
    panel = np.zeros((height, width, 3), dtype=np.uint8)
    lines = [
        "Fusion Validation",
        f"Raw LiDAR points: {metrics['raw_lidar_points']}",
        f"Front LiDAR points: {metrics['front_lidar_points']}",
        f"Projected in image: {metrics['projected_points']}",
        f"Valid RS depth: {metrics['valid_depth_pairs']}",
    ]

    depth_stats = metrics["depth_error_mm"]
    if depth_stats["mean"] is not None:
        lines.extend([
            f"Depth error mean: {depth_stats['mean']:.1f} mm",
            f"Depth error median: {depth_stats['median']:.1f} mm",
            f"Depth error max: {depth_stats['max']:.1f} mm",
            f"Depth error std: {depth_stats['std']:.1f} mm",
        ])
    else:
        lines.append("Depth error: no valid pairs")

    lines.extend([
        "",
        "S: save frame + metrics",
        "Q: quit",
    ])

    y = 36
    for i, line in enumerate(lines):
        color = (0, 255, 255) if i == 0 else (230, 230, 230)
        cv2.putText(panel, line, (24, y), cv2.FONT_HERSHEY_SIMPLEX, 0.72, color, 2)
        y += 34

    return panel


def process_scan(scan, color_img, depth_img, depth_scale, K, dist_coeffs, R, T, rvec, tvec):
    lidar_points, raw_count, front_count = scan_to_lidar_points(scan)
    projected, z_camera_mm = project_lidar_points(lidar_points, K, dist_coeffs, R, T, rvec, tvec)

    overlay = color_img.copy()
    sparse_depth = np.zeros((COLOR_HEIGHT, COLOR_WIDTH), dtype=np.uint16)
    depth_errors = []
    projected_count = 0
    valid_depth_pairs = 0

    for (u_float, v_float), z_mm in zip(projected, z_camera_mm):
        if z_mm <= 0:
            continue

        u = int(round(u_float))
        v = int(round(v_float))
        if not (0 <= u < COLOR_WIDTH and 0 <= v < COLOR_HEIGHT):
            continue

        projected_count += 1
        lidar_depth_mm = float(z_mm)
        sparse_depth[v, u] = int(np.clip(lidar_depth_mm, 0, 65535))

        rs_depth_raw = int(depth_img[v, u])
        rs_depth_mm = rs_depth_raw * depth_scale * 1000.0

        if rs_depth_raw > 0:
            valid_depth_pairs += 1
            depth_errors.append(abs(lidar_depth_mm - rs_depth_mm))
            color = (0, 255, 0)
        else:
            color = (0, 255, 255)

        cv2.circle(overlay, (u, v), 2, color, -1)

    metrics = {
        "raw_lidar_points": int(raw_count),
        "front_lidar_points": int(front_count),
        "projected_points": int(projected_count),
        "valid_depth_pairs": int(valid_depth_pairs),
        "depth_error_mm": summarize(np.array(depth_errors, dtype=np.float64)),
    }

    return overlay, sparse_depth, metrics


def save_frame(color_img, depth_img, sparse_depth, overlay, metrics, timestamp):
    idx = str(timestamp)
    paths = {
        "rgb": os.path.join(OUTPUT_DIR, "rgb", f"rgb_{idx}.png"),
        "depth_dense": os.path.join(OUTPUT_DIR, "depth_dense", f"depth_dense_{idx}.png"),
        "depth_sparse": os.path.join(OUTPUT_DIR, "depth_sparse", f"depth_sparse_{idx}.png"),
        "fusion": os.path.join(OUTPUT_DIR, "fusion", f"fusion_{idx}.png"),
        "metrics": os.path.join(OUTPUT_DIR, "metrics", f"metrics_{idx}.json"),
    }

    cv2.imwrite(paths["rgb"], color_img)
    cv2.imwrite(paths["depth_dense"], depth_img)
    cv2.imwrite(paths["depth_sparse"], sparse_depth)
    cv2.imwrite(paths["fusion"], overlay)

    payload = {
        "timestamp": timestamp,
        "timestamp_iso": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp / 1000)),
        "calibration_file": CALIB_FILE,
        "lidar_port": PORT,
        "metrics": metrics,
        "files": {key: os.path.relpath(value, PROJECT_ROOT) for key, value in paths.items()},
    }

    with open(paths["metrics"], "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Saved fusion frame {idx}")


# ==============================
# MAIN LOOP
# ==============================
def main():
    ensure_output_dirs()
    K, dist_coeffs, R, T, rvec, tvec = load_calibration()

    lidar = None
    pipeline = None

    try:
        pipeline, align, depth_scale = init_realsense()
        lidar = init_lidar()

        for scan in lidar.iter_scans():
            frames = pipeline.wait_for_frames()
            aligned = align.process(frames)

            depth_frame = aligned.get_depth_frame()
            color_frame = aligned.get_color_frame()

            if not depth_frame or not color_frame:
                continue

            color_img = np.asanyarray(color_frame.get_data())
            depth_img = np.asanyarray(depth_frame.get_data())

            overlay, sparse_depth, metrics = process_scan(
                scan, color_img, depth_img, depth_scale, K, dist_coeffs, R, T, rvec, tvec
            )

            depth_cm = cv2.applyColorMap(
                cv2.convertScaleAbs(depth_img, alpha=0.03),
                cv2.COLORMAP_JET
            )
            sparse_cm = render_sparse_depth(sparse_depth)
            panel = make_metrics_panel(metrics)

            top = np.hstack((overlay, depth_cm))
            bottom = np.hstack((sparse_cm, panel))
            combined = np.vstack((top, bottom))

            cv2.imshow("Fusion Validation", combined)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("s"):
                ts = int(time.time() * 1000)
                save_frame(color_img, depth_img, sparse_depth, overlay, metrics, ts)

            if key == ord("q"):
                break

    finally:
        if lidar is not None:
            try:
                lidar.stop()
                lidar.disconnect()
            except Exception:
                pass
        if pipeline is not None:
            try:
                pipeline.stop()
            except Exception:
                pass
        cv2.destroyAllWindows()
        print("Cleaned up.")


if __name__ == "__main__":
    main()
