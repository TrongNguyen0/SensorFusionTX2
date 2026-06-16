import glob
import json
import os
import sys
import time

import cv2
import numpy as np
import pyrealsense2 as rs

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ==============================
# CONFIG
# ==============================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALIBRATION_DIR = os.path.join(PROJECT_ROOT, "data", "captured_data", "pair")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "calibration_result_pnp.npz")
RESULT_DIR = os.path.join(PROJECT_ROOT, "data", "calibration_result")
METRICS_FILE = os.path.join(RESULT_DIR, "calibration_metrics.json")
PREVIEW_DIR = os.path.join(RESULT_DIR, "reprojection_preview")

COLOR_WIDTH = 640
COLOR_HEIGHT = 480
CAMERA_FPS = 30
RANSAC_ITERATIONS = 1000
RANSAC_REPROJECTION_ERROR = 8.0
RANSAC_CONFIDENCE = 0.99
PNP_FLAGS = cv2.SOLVEPNP_IPPE
MAX_PREVIEW_IMAGES = 8


def ensure_output_dirs():
    os.makedirs(RESULT_DIR, exist_ok=True)
    os.makedirs(PREVIEW_DIR, exist_ok=True)


def to_jsonable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.float32, np.float64)):
        return float(value)
    if isinstance(value, (np.int32, np.int64)):
        return int(value)
    return value


def imread_unicode(path):
    if not os.path.exists(path):
        return None
    data = np.fromfile(path, dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def imwrite_unicode(path, image):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ext = os.path.splitext(path)[1]
    success, encoded = cv2.imencode(ext, image)
    if not success:
        return False
    encoded.tofile(path)
    return True


def source_image_candidates(json_path):
    basename = os.path.splitext(os.path.basename(json_path))[0]
    timestamp = basename.replace("pair_", "")
    pair_image = os.path.splitext(json_path)[0] + ".png"
    color_image = os.path.join(PROJECT_ROOT, "data", "captured_data", "color", f"color_{timestamp}.png")
    return [pair_image, color_image]


# ==============================
# CAMERA INTRINSICS
# ==============================
def get_camera_intrinsics():
    print("Initializing RealSense for camera intrinsics...")
    ctx = rs.context()
    devices = ctx.query_devices()
    if len(devices) == 0:
        raise RuntimeError(
            "No RealSense device connected. Cannot read camera intrinsics. "
            "Reconnect the camera or close other apps using it."
        )

    device = devices[0]
    camera_info = {}
    for key, label in [
        (rs.camera_info.name, "name"),
        (rs.camera_info.serial_number, "serial_number"),
        (rs.camera_info.firmware_version, "firmware_version"),
    ]:
        try:
            camera_info[label] = device.get_info(key)
        except Exception:
            camera_info[label] = None

    if camera_info.get("name"):
        print(f"RealSense Device: {camera_info['name']} (S/N: {camera_info.get('serial_number')})")

    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, COLOR_WIDTH, COLOR_HEIGHT, rs.format.bgr8, CAMERA_FPS)

    profile = None
    try:
        profile = pipeline.start(config)
        time.sleep(1)
        intr = profile.get_stream(rs.stream.color).as_video_stream_profile().get_intrinsics()
    finally:
        if profile is not None:
            pipeline.stop()

    K = np.array([
        [intr.fx, 0, intr.ppx],
        [0, intr.fy, intr.ppy],
        [0, 0, 1]
    ], dtype=np.float64)

    dist_coeffs = np.array(intr.coeffs, dtype=np.float64)

    print("Camera Intrinsics:")
    print(K)
    print("Distortion:", dist_coeffs)

    return K, dist_coeffs, camera_info


# ==============================
# LOAD DATA
# ==============================
def polar_to_lidar_point(angle_deg, distance_mm):
    angle = np.radians(angle_deg)
    x = distance_mm * np.sin(angle)
    z = distance_mm * np.cos(angle)
    return [x, 0.0, z]


def load_data():
    json_files = sorted(glob.glob(os.path.join(CALIBRATION_DIR, "pair_*.json")))
    if len(json_files) == 0:
        raise RuntimeError(f"No calibration JSON files found in {CALIBRATION_DIR}")

    lidar_pts = []
    pixel_pts = []
    records = []
    file_stats = []

    for jf in json_files:
        with open(jf, "r", encoding="utf-8") as f:
            data = json.load(f)

        mapped_points = data.get("mapped_points", [])
        valid_count = 0

        for idx, pt in enumerate(mapped_points):
            required = ["angle", "distance", "pixel_x", "pixel_y"]
            if any(key not in pt for key in required):
                continue

            lidar_pt = polar_to_lidar_point(pt["angle"], pt["distance"])
            pixel_pt = [pt["pixel_x"], pt["pixel_y"]]

            lidar_pts.append(lidar_pt)
            pixel_pts.append(pixel_pt)
            records.append({
                "source_json": jf,
                "source_image_candidates": source_image_candidates(jf),
                "point_index": idx,
                "angle": pt["angle"],
                "distance": pt["distance"],
                "pixel_x": pt["pixel_x"],
                "pixel_y": pt["pixel_y"],
            })
            valid_count += 1

        file_stats.append({
            "file": os.path.basename(jf),
            "mapped_points": len(mapped_points),
            "valid_points": valid_count,
        })

    lidar_pts = np.array(lidar_pts, dtype=np.float64)
    pixel_pts = np.array(pixel_pts, dtype=np.float64)

    if len(lidar_pts) < 4:
        raise RuntimeError(f"Not enough correspondences for PnP: {len(lidar_pts)} found")

    print(f"Loaded {len(json_files)} pair files")
    print(f"Loaded {len(lidar_pts)} valid correspondences")

    return lidar_pts, pixel_pts, records, file_stats


# ==============================
# PNP + RANSAC
# ==============================
def solve_pnp(lidar_pts, pixel_pts, K, dist_coeffs):
    success, rvec, tvec, inliers = cv2.solvePnPRansac(
        lidar_pts,
        pixel_pts,
        K,
        dist_coeffs,
        flags=PNP_FLAGS,
        iterationsCount=RANSAC_ITERATIONS,
        reprojectionError=RANSAC_REPROJECTION_ERROR,
        confidence=RANSAC_CONFIDENCE
    )

    if not success or inliers is None or len(inliers) == 0:
        raise RuntimeError("PnP failed or produced no inliers")

    R, _ = cv2.Rodrigues(rvec)
    T = tvec.reshape(3, 1)
    inlier_indices = inliers.flatten().astype(np.int32)

    print(f"Inliers: {len(inlier_indices)}/{len(lidar_pts)}")

    return rvec, tvec, R, T, inlier_indices


# ==============================
# ERROR
# ==============================
def compute_reprojection(lidar_pts, pixel_pts, rvec, tvec, K, dist_coeffs, inlier_indices):
    projected, _ = cv2.projectPoints(lidar_pts, rvec, tvec, K, dist_coeffs)
    projected = projected.reshape(-1, 2)
    all_errors = np.linalg.norm(projected - pixel_pts, axis=1)
    inlier_errors = all_errors[inlier_indices]

    metrics = {
        "total_correspondences": int(len(lidar_pts)),
        "inlier_count": int(len(inlier_indices)),
        "outlier_count": int(len(lidar_pts) - len(inlier_indices)),
        "inlier_ratio": float(len(inlier_indices) / len(lidar_pts)),
        "reprojection_error_px": {
            "all": summarize_errors(all_errors),
            "inliers": summarize_errors(inlier_errors),
        }
    }

    print("Reprojection Error (inliers):")
    print(f"Mean: {metrics['reprojection_error_px']['inliers']['mean']:.2f} px")
    print(f"Median: {metrics['reprojection_error_px']['inliers']['median']:.2f} px")
    print(f"Max: {metrics['reprojection_error_px']['inliers']['max']:.2f} px")
    print(f"Std: {metrics['reprojection_error_px']['inliers']['std']:.2f} px")

    return projected, all_errors, metrics


def summarize_errors(errors):
    if len(errors) == 0:
        return {
            "mean": None,
            "median": None,
            "max": None,
            "std": None,
        }
    return {
        "mean": float(np.mean(errors)),
        "median": float(np.median(errors)),
        "max": float(np.max(errors)),
        "std": float(np.std(errors)),
    }


def build_point_report(records, projected, all_errors, inlier_indices):
    inlier_set = set(int(i) for i in inlier_indices)
    report = []
    for idx, record in enumerate(records):
        report.append({
            "source_json": os.path.basename(record["source_json"]),
            "point_index": int(record["point_index"]),
            "angle": float(record["angle"]),
            "distance": float(record["distance"]),
            "observed_pixel": [float(record["pixel_x"]), float(record["pixel_y"])],
            "projected_pixel": [float(projected[idx, 0]), float(projected[idx, 1])],
            "error_px": float(all_errors[idx]),
            "is_inlier": idx in inlier_set,
        })
    return report


def save_preview_images(records, projected, all_errors, inlier_indices):
    inlier_set = set(int(i) for i in inlier_indices)
    grouped = {}
    for idx, record in enumerate(records):
        key = tuple(record["source_image_candidates"])
        grouped.setdefault(key, []).append(idx)

    saved = []
    missing = 0
    for image_candidates, indices in list(grouped.items())[:MAX_PREVIEW_IMAGES]:
        image = None
        image_path = None
        for candidate in image_candidates:
            image = imread_unicode(candidate)
            if image is not None:
                image_path = candidate
                break

        if image is None or image_path is None:
            missing += 1
            continue

        for idx in indices:
            observed = (int(round(records[idx]["pixel_x"])), int(round(records[idx]["pixel_y"])))
            reproj = (int(round(projected[idx, 0])), int(round(projected[idx, 1])))
            color = (0, 255, 0) if idx in inlier_set else (0, 0, 255)
            cv2.circle(image, observed, 4, (255, 0, 0), -1)
            cv2.circle(image, reproj, 3, color, -1)
            cv2.line(image, observed, reproj, (0, 255, 255), 1)

        basename = os.path.basename(image_path)
        out_path = os.path.join(PREVIEW_DIR, f"reprojection_{basename}")
        imwrite_unicode(out_path, image)
        saved.append(out_path)

    print(f"Saved {len(saved)} reprojection preview images")
    if missing:
        print(f"Skipped {missing} preview source images that could not be read")
    return saved


def save_results(K, dist_coeffs, rvec, tvec, R, T, inlier_indices, projected, all_errors,
                 metrics, file_stats, point_report, preview_paths, camera_info):
    np.savez(
        OUTPUT_FILE,
        K=K,
        distCoeffs=dist_coeffs,
        rvec=rvec,
        tvec=tvec,
        R=R,
        T=T,
        inlier_indices=inlier_indices,
        projected_points=projected,
        reprojection_errors=all_errors,
    )

    result = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "calibration_dir": CALIBRATION_DIR,
        "output_file": OUTPUT_FILE,
        "camera_info": camera_info,
        "camera_intrinsics": {
            "K": K,
            "distCoeffs": dist_coeffs,
        },
        "ransac_config": {
            "iterations": RANSAC_ITERATIONS,
            "reprojection_error_px": RANSAC_REPROJECTION_ERROR,
            "confidence": RANSAC_CONFIDENCE,
            "pnp_flag": "SOLVEPNP_IPPE",
        },
        "extrinsics": {
            "R": R,
            "T": T,
            "rvec": rvec,
            "tvec": tvec,
        },
        "metrics": metrics,
        "file_stats": file_stats,
        "preview_images": [os.path.relpath(p, PROJECT_ROOT) for p in preview_paths],
        "point_report": point_report,
    }

    with open(METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=to_jsonable)

    print("\nSaved calibration:", OUTPUT_FILE)
    print("Saved metrics:", METRICS_FILE)


# ==============================
# MAIN
# ==============================
def main():
    ensure_output_dirs()

    K, dist_coeffs, camera_info = get_camera_intrinsics()
    lidar_pts, pixel_pts, records, file_stats = load_data()

    rvec, tvec, R, T, inlier_indices = solve_pnp(lidar_pts, pixel_pts, K, dist_coeffs)
    projected, all_errors, metrics = compute_reprojection(
        lidar_pts, pixel_pts, rvec, tvec, K, dist_coeffs, inlier_indices
    )
    point_report = build_point_report(records, projected, all_errors, inlier_indices)
    preview_paths = save_preview_images(records, projected, all_errors, inlier_indices)

    save_results(
        K, dist_coeffs, rvec, tvec, R, T, inlier_indices,
        projected, all_errors, metrics, file_stats, point_report, preview_paths, camera_info
    )

    print("\n== K ==\n", K)
    print("\n== distCoeffs ==\n", dist_coeffs)
    print("\n== R ==\n", R)
    print("\n== T ==\n", T)
    print("\n=== USE ===")
    print("camera = R @ lidar + T")
    print("pixel = cv2.projectPoints(lidar_points, rvec, tvec, K, distCoeffs)")


if __name__ == "__main__":
    main()
