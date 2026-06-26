import json
import os
import time

import cv2

from .lidar_core import (
    CORNER_FIT_DISTANCE_THRESHOLD_MM,
    CORNER_FIT_MIN_POINTS_PER_SIDE,
    CORNER_RANSAC_MIN_INLIER_RATIO,
    CORNER_RANSAC_RESIDUAL_THRESHOLD_MM,
    FRONT_ANGLE_MAX,
    FRONT_ANGLE_MIN,
    polar_to_cartesian,
)


REQUIRED_CALIBRATION_POINTS = 3


def build_correspondences(lidar_points, image_points):
    if len(lidar_points) != len(image_points):
        raise ValueError("LiDAR and image point counts must match")
    if len(lidar_points) != REQUIRED_CALIBRATION_POINTS:
        raise ValueError(f"Expected {REQUIRED_CALIBRATION_POINTS} calibration points")

    correspondences = []
    for index, (lidar_point, image_point) in enumerate(zip(lidar_points, image_points), start=1):
        role = None
        source = None
        if isinstance(lidar_point, dict):
            angle = lidar_point["angle_deg"]
            distance = lidar_point["distance_mm"]
            x = lidar_point.get("x_mm")
            z = lidar_point.get("z_mm")
            if x is None or z is None:
                x, z = polar_to_cartesian(angle, distance)
            role = lidar_point.get("role")
            source = lidar_point.get("source")
        else:
            _, angle, distance = lidar_point
            x, z = polar_to_cartesian(angle, distance)

        u, v = image_point
        item = {
            "id": index,
            "lidar": {
                "angle_deg": float(angle),
                "distance_mm": float(distance),
                "x_mm": float(x),
                "y_mm": 0.0,
                "z_mm": float(z),
            },
            "image": {
                "u": int(u),
                "v": int(v),
            },
        }
        if role is not None:
            item["role"] = role
        if source is not None:
            item["lidar"]["source"] = source
        correspondences.append(item)
    return correspondences


def build_calibration_data(
    timestamp,
    correspondences,
    project_config,
    manual_lidar_clicks=None,
    lidar_feature_extraction=None,
):
    distances = [item["lidar"]["distance_mm"] for item in correspondences]

    return {
        "timestamp": timestamp,
        "timestamp_iso": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp / 1000)),
        "source_script": "app_pyqt.py",
        "data_version": "corner_feature_correspondence_v2",
        "calibration_method": "guided_v_shape_lidar_tls_features",
        "hardware": {
            "lidar_model": "RPLidar A1M8",
            "lidar_port": project_config["lidar_port"],
            "camera_model": "Intel RealSense D435",
            "camera_lidar_vertical_offset_mm": project_config.get("camera_lidar_vertical_offset_mm"),
            "camera_lidar_forward_offset_mm": project_config.get("camera_lidar_forward_offset_mm"),
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
        "target_model": {
            "type": "corner_target",
            "point_order": [
                "left_edge_feature",
                "corner_intersection_feature",
                "right_edge_feature",
            ],
            "points_per_snapshot": REQUIRED_CALIBRATION_POINTS,
        },
        "correspondence_count": len(correspondences),
        "avg_distance_mm": sum(distances) / len(distances) if distances else None,
        "lidar_selection_method": "manual_guided_ransac_tls_line_fit",
        "lidar_snapshot_source": project_config.get("lidar_snapshot_source"),
        "lidar_feature_fit_config": {
            "distance_threshold_mm": CORNER_FIT_DISTANCE_THRESHOLD_MM,
            "min_points_per_side": CORNER_FIT_MIN_POINTS_PER_SIDE,
            "ransac_residual_threshold_mm": CORNER_RANSAC_RESIDUAL_THRESHOLD_MM,
            "ransac_min_inlier_ratio": CORNER_RANSAC_MIN_INLIER_RATIO,
        },
        "realtime_preview_method": project_config.get("realtime_preview_method"),
        "realtime_preview_smooth_scans": project_config.get("realtime_preview_smooth_scans"),
        "realtime_preview_angle_bin_deg": project_config.get("realtime_preview_angle_bin_deg"),
        "manual_lidar_clicks": manual_lidar_clicks or [],
        "lidar_feature_extraction": lidar_feature_extraction or {},
        "correspondences": correspondences,
    }


def render_pair_preview(color_img, correspondences):
    preview = color_img.copy()
    image_points = [
        (item["image"]["u"], item["image"]["v"])
        for item in correspondences
    ]
    colors = [(0, 255, 0), (0, 220, 255), (0, 0, 255)]

    for idx in range(len(image_points) - 1):
        cv2.line(preview, image_points[idx], image_points[idx + 1], (255, 255, 0), 2)

    for idx, point in enumerate(image_points):
        color = colors[idx % len(colors)]
        cv2.circle(preview, point, 6, color, -1)
        cv2.putText(
            preview,
            f"P{idx + 1}",
            (point[0] + 8, point[1] - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )
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
