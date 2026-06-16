import json
import os
import time

import cv2

from .lidar_core import (
    ANGLE_BIN_DEG,
    BAR_DISTANCE_JUMP_THRESHOLD_MM,
    DENOISE_SCAN_COUNT,
    FRONT_ANGLE_MAX,
    FRONT_ANGLE_MIN,
    polar_to_cartesian,
)


def map_lidar_to_image(bar_points, p1, p2):
    if not bar_points:
        return []
    if p1[0] >= p2[0]:
        return []

    angles = [angle for _, angle, _ in bar_points]
    min_angle = min(angles)
    max_angle = max(angles)

    mapped = []
    for _, angle, distance in bar_points:
        if max_angle != min_angle:
            t = (angle - min_angle) / (max_angle - min_angle)
        else:
            t = 0.5

        px = int(p1[0] + t * (p2[0] - p1[0]))
        py = int(p1[1] + t * (p2[1] - p1[1]))
        mapped.append({
            "angle": angle,
            "distance": distance,
            "pixel_x": px,
            "pixel_y": py,
        })
    return mapped


def build_calibration_data(timestamp, bar_points, mapped_points, image_p1, image_p2, project_config):
    angles = [angle for _, angle, _ in bar_points]
    distances = [distance for _, _, distance in bar_points]

    cartesian_points = []
    for _, angle, distance in bar_points:
        x, z = polar_to_cartesian(angle, distance)
        cartesian_points.append({
            "angle": angle,
            "distance": distance,
            "x": x,
            "z": z,
        })

    return {
        "timestamp": timestamp,
        "timestamp_iso": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp / 1000)),
        "source_script": "app_pyqt.py",
        "hardware": {
            "lidar_model": "RPLidar A1M8",
            "lidar_port": project_config["lidar_port"],
            "camera_model": "Intel RealSense D435",
        },
        "capture_config": {
            "color_width": project_config["color_width"],
            "color_height": project_config["color_height"],
            "depth_width": project_config["depth_width"],
            "depth_height": project_config["depth_height"],
            "fps": project_config["fps"],
            "front_angle_min_deg": FRONT_ANGLE_MIN,
            "front_angle_max_deg": FRONT_ANGLE_MAX,
        },
        "image_point_start": image_p1,
        "image_point_end": image_p2,
        "lidar_angle_min": min(angles),
        "lidar_angle_max": max(angles),
        "lidar_points_count": len(bar_points),
        "mapped_points_count": len(mapped_points),
        "avg_distance": sum(distances) / len(distances),
        "denoising_method": "multi_scan_angle_binning_median",
        "denoising_scans_count": DENOISE_SCAN_COUNT,
        "angle_bin_deg": ANGLE_BIN_DEG,
        "bar_distance_jump_threshold_mm": BAR_DISTANCE_JUMP_THRESHOLD_MM,
        "cartesian_points": cartesian_points,
        "mapped_points": mapped_points,
    }


def render_pair_preview(color_img, mapped_points, image_p1, image_p2):
    preview = color_img.copy()
    cv2.line(preview, tuple(image_p1), tuple(image_p2), (255, 255, 0), 2)
    for point in mapped_points:
        cv2.circle(preview, (point["pixel_x"], point["pixel_y"]), 3, (0, 255, 0), -1)
    return preview


def imwrite_unicode(path, image):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ext = os.path.splitext(path)[1]
    success, encoded = cv2.imencode(ext, image)
    if not success:
        return False
    encoded.tofile(path)
    return True


def save_sample(output_dir, color_img, depth_img, preview_img, calibration_data, timestamp):
    color_dir = os.path.join(output_dir, "color")
    depth_dir = os.path.join(output_dir, "depth")
    depth_cm_dir = os.path.join(output_dir, "depth_colormap")
    pair_dir = os.path.join(output_dir, "pair")

    for directory in [color_dir, depth_dir, depth_cm_dir, pair_dir]:
        os.makedirs(directory, exist_ok=True)

    color_path = os.path.join(color_dir, f"color_{timestamp}.png")
    depth_path = os.path.join(depth_dir, f"depth_{timestamp}.png")
    depth_cm_path = os.path.join(depth_cm_dir, f"depth_colormap_{timestamp}.png")
    pair_img_path = os.path.join(pair_dir, f"pair_{timestamp}.png")
    pair_json_path = os.path.join(pair_dir, f"pair_{timestamp}.json")

    imwrite_unicode(color_path, color_img)
    imwrite_unicode(depth_path, depth_img)
    depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_img, alpha=0.03), cv2.COLORMAP_JET)
    imwrite_unicode(depth_cm_path, depth_colormap)
    imwrite_unicode(pair_img_path, preview_img)

    with open(pair_json_path, "w", encoding="utf-8") as file:
        json.dump(calibration_data, file, indent=2)

    return {
        "color": color_path,
        "depth": depth_path,
        "depth_colormap": depth_cm_path,
        "pair_image": pair_img_path,
        "pair_json": pair_json_path,
    }
