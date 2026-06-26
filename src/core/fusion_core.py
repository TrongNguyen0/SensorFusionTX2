import json
import math
import os
import time

import cv2
import numpy as np


FRONT_ANGLE_MIN = -90
FRONT_ANGLE_MAX = 90
MAX_DEPTH_MM = 6000


def imwrite_unicode(path, image):
    ext = os.path.splitext(path)[1]
    ok, encoded = cv2.imencode(ext, image)
    if not ok:
        raise IOError(f"Could not encode image for: {path}")
    encoded.tofile(path)


def next_output_index(output_dir):
    max_index = -1
    for subdir in ["rgb", "depth_dense", "depth_sparse", "fusion", "metrics"]:
        folder = os.path.join(output_dir, subdir)
        if not os.path.isdir(folder):
            continue
        for filename in os.listdir(folder):
            stem, _ = os.path.splitext(filename)
            if stem.isdigit():
                max_index = max(max_index, int(stem))
    return max_index + 1


def load_calibration(calib_file):
    if not os.path.exists(calib_file):
        raise FileNotFoundError(f"Calibration file not found: {calib_file}")

    data = np.load(calib_file)
    K = data["K"]
    R = data["R"]
    T = data["T"].reshape(3, 1)

    if "distCoeffs" in data:
        dist_coeffs = data["distCoeffs"].reshape(-1, 1)
    else:
        dist_coeffs = np.zeros((5, 1), dtype=np.float64)

    if "rvec" in data:
        rvec = data["rvec"].reshape(3, 1)
    else:
        rvec, _ = cv2.Rodrigues(R)

    if "tvec" in data:
        tvec = data["tvec"].reshape(3, 1)
    else:
        tvec = T

    return K, dist_coeffs, R, T, rvec, tvec


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


def render_dense_depth(depth_img):
    return cv2.applyColorMap(
        cv2.convertScaleAbs(depth_img, alpha=0.03),
        cv2.COLORMAP_JET,
    )


def render_sparse_depth(sparse_depth):
    clipped = np.clip(sparse_depth.astype(np.float32), 0, MAX_DEPTH_MM)
    depth_8u = cv2.convertScaleAbs(clipped, alpha=255.0 / MAX_DEPTH_MM)
    depth_cm = cv2.applyColorMap(depth_8u, cv2.COLORMAP_JET)
    depth_cm[sparse_depth == 0] = (0, 0, 0)
    return depth_cm


def process_scan(scan, color_img, depth_img, depth_scale, K, dist_coeffs, R, T, rvec, tvec):
    height, width = depth_img.shape[:2]
    lidar_points, raw_count, front_count = scan_to_lidar_points(scan)
    projected, z_camera_mm = project_lidar_points(lidar_points, K, dist_coeffs, R, T, rvec, tvec)

    overlay = color_img.copy()
    sparse_depth = np.zeros((height, width), dtype=np.uint16)
    depth_errors = []
    projected_count = 0
    valid_depth_pairs = 0

    for (u_float, v_float), z_mm in zip(projected, z_camera_mm):
        if z_mm <= 0:
            continue

        u = int(round(u_float))
        v = int(round(v_float))
        if not (0 <= u < width and 0 <= v < height):
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


def metrics_to_text(metrics):
    depth_stats = metrics["depth_error_mm"]
    lines = [
        "Fusion Validation",
        f"Raw scan points: {metrics.get('raw_scan_points', '-')}",
        f"Filtered scan points: {metrics.get('filtered_scan_points', '-')}",
        f"Denoise scans: {metrics.get('fusion_denoise_scans', '-')}",
        f"Denoised LiDAR points: {metrics['raw_lidar_points']}",
        f"Front valid points: {metrics['front_lidar_points']}",
        f"Projected in image: {metrics['projected_points']}",
        f"Valid RS depth pairs: {metrics['valid_depth_pairs']}",
    ]
    if depth_stats["mean"] is None:
        lines.append("Depth error: no valid pairs")
    else:
        lines.extend([
            f"Depth error mean: {depth_stats['mean']:.1f} mm",
            f"Depth error median: {depth_stats['median']:.1f} mm",
            f"Depth error max: {depth_stats['max']:.1f} mm",
            f"Depth error std: {depth_stats['std']:.1f} mm",
        ])
    return "\n".join(lines)


def save_fusion_frame(output_dir, project_root, calib_file, lidar_port,
                      color_img, depth_img, sparse_depth, overlay, metrics, timestamp):
    index = next_output_index(output_dir)
    frame_id = f"{index:06d}"
    paths = {
        "rgb": os.path.join(output_dir, "rgb", f"{frame_id}.png"),
        "depth_dense": os.path.join(output_dir, "depth_dense", f"{frame_id}.png"),
        "depth_sparse": os.path.join(output_dir, "depth_sparse", f"{frame_id}.png"),
        "fusion": os.path.join(output_dir, "fusion", f"{frame_id}.png"),
        "metrics": os.path.join(output_dir, "metrics", f"{frame_id}.json"),
    }

    for path in paths.values():
        os.makedirs(os.path.dirname(path), exist_ok=True)

    imwrite_unicode(paths["rgb"], color_img)
    imwrite_unicode(paths["depth_dense"], depth_img)
    imwrite_unicode(paths["depth_sparse"], sparse_depth)
    imwrite_unicode(paths["fusion"], overlay)

    payload = {
        "frame_id": frame_id,
        "sequence_index": index,
        "timestamp": timestamp,
        "timestamp_iso": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp / 1000)),
        "calibration_file": calib_file,
        "lidar_port": lidar_port,
        "metrics": metrics,
        "files": {key: os.path.relpath(value, project_root) for key, value in paths.items()},
    }

    with open(paths["metrics"], "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    return paths
