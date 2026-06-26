import math
import statistics

import numpy as np


FRONT_ANGLE_MIN = -90
FRONT_ANGLE_MAX = 90
DENOISE_SCAN_COUNT = 10
ANGLE_BIN_DEG = 1
DISPLAY_SMOOTH_SCAN_COUNT = 4
DISPLAY_SMOOTH_ANGLE_BIN_DEG = 0.5
CORNER_FIT_DISTANCE_THRESHOLD_MM = 120.0
CORNER_FIT_MIN_POINTS_PER_SIDE = 3
CORNER_RANSAC_RESIDUAL_THRESHOLD_MM = 45.0
CORNER_RANSAC_MIN_INLIER_RATIO = 0.45


def normalize_angle(angle_deg):
    if angle_deg > 180:
        return angle_deg - 360
    return angle_deg


def polar_to_cartesian(angle_deg, distance_mm):
    angle_rad = math.radians(angle_deg)
    x = distance_mm * math.sin(angle_rad)
    z = distance_mm * math.cos(angle_rad)
    return x, z


def cartesian_to_polar(x_mm, z_mm):
    distance = math.hypot(x_mm, z_mm)
    angle = math.degrees(math.atan2(x_mm, z_mm))
    return angle, distance


def filter_scan(scan_data, front_min=FRONT_ANGLE_MIN, front_max=FRONT_ANGLE_MAX):
    filtered = []
    for quality, angle, distance in scan_data:
        norm_angle = normalize_angle(angle)
        if front_min <= norm_angle <= front_max and distance > 0:
            filtered.append((quality, norm_angle, distance))
    filtered.sort(key=lambda item: item[1])
    return filtered


def denoise_scans(scans, num_scans=DENOISE_SCAN_COUNT, angle_bin_deg=ANGLE_BIN_DEG):
    scans_to_use = scans[-num_scans:] if len(scans) >= num_scans else list(scans)
    if not scans_to_use:
        return []

    angle_dist_map = {}
    for scan in scans_to_use:
        for _, angle, distance in scan:
            if distance <= 0:
                continue
            angle_bin = round(angle / angle_bin_deg) * angle_bin_deg
            angle_dist_map.setdefault(angle_bin, []).append(distance)

    denoised = []
    for angle_bin in sorted(angle_dist_map.keys()):
        distances = angle_dist_map[angle_bin]
        denoised.append((0, angle_bin, statistics.median(distances)))
    return denoised


def smooth_scan_for_display(
    scans,
    num_scans=DISPLAY_SMOOTH_SCAN_COUNT,
    angle_bin_deg=DISPLAY_SMOOTH_ANGLE_BIN_DEG,
):
    scans_to_use = scans[-num_scans:] if len(scans) >= num_scans else list(scans)
    if not scans_to_use:
        return []

    angle_dist_map = {}
    for scan in scans_to_use:
        for _, angle, distance in scan:
            if distance <= 0:
                continue
            angle_bin = round(angle / angle_bin_deg) * angle_bin_deg
            angle_dist_map.setdefault(angle_bin, []).append(distance)

    smoothed = []
    for angle_bin in sorted(angle_dist_map.keys()):
        distances = angle_dist_map[angle_bin]
        smoothed.append((0, angle_bin, statistics.median(distances)))
    return smoothed


def scan_to_xz_points(scan_data):
    points = []
    for _, angle, distance in scan_data:
        if distance <= 0:
            continue
        x, z = polar_to_cartesian(angle, distance)
        points.append([x, z])
    return np.array(points, dtype=np.float64)


def point_to_segment_distance(point, start, end):
    segment = end - start
    length_sq = float(np.dot(segment, segment))
    if length_sq <= 1e-9:
        return float(np.linalg.norm(point - start)), 0.0

    t = float(np.dot(point - start, segment) / length_sq)
    t_clamped = min(1.0, max(0.0, t))
    closest = start + t_clamped * segment
    return float(np.linalg.norm(point - closest)), t


def select_points_near_segment(points, start, end, threshold_mm):
    selected = []
    for point in points:
        distance, t = point_to_segment_distance(point, start, end)
        if -0.1 <= t <= 1.1 and distance <= threshold_mm:
            selected.append(point)
    return np.array(selected, dtype=np.float64)


def fit_line_tls(points):
    if len(points) < 2:
        raise ValueError("At least 2 points are required to fit a line")

    centroid = points.mean(axis=0)
    centered = points - centroid
    _, _, vh = np.linalg.svd(centered, full_matrices=False)
    direction = vh[0]
    norm = float(np.linalg.norm(direction))
    if norm <= 1e-9:
        raise ValueError("Degenerate line fit")
    direction = direction / norm
    return centroid, direction


def line_residuals(points, line_point, line_direction):
    normal = np.array([-line_direction[1], line_direction[0]], dtype=np.float64)
    return np.abs((points - line_point) @ normal)


def summarize_residuals(residuals):
    if len(residuals) == 0:
        return {
            "mean_mm": None,
            "median_mm": None,
            "max_mm": None,
            "std_mm": None,
        }
    return {
        "mean_mm": float(np.mean(residuals)),
        "median_mm": float(np.median(residuals)),
        "max_mm": float(np.max(residuals)),
        "std_mm": float(np.std(residuals)),
    }


def fit_line_ransac_then_tls(points, residual_threshold_mm, min_points, min_inlier_ratio):
    if len(points) < min_points:
        raise ValueError(f"Need at least {min_points} support points, got {len(points)}")

    best_inliers = None
    best_count = -1
    best_median = float("inf")

    for i in range(len(points) - 1):
        for j in range(i + 1, len(points)):
            p1 = points[i]
            p2 = points[j]
            direction = p2 - p1
            norm = float(np.linalg.norm(direction))
            if norm <= 1e-9:
                continue

            direction = direction / norm
            residuals = line_residuals(points, p1, direction)
            inliers = residuals <= residual_threshold_mm
            count = int(np.count_nonzero(inliers))
            median = float(np.median(residuals[inliers])) if count else float("inf")

            if count > best_count or (count == best_count and median < best_median):
                best_inliers = inliers
                best_count = count
                best_median = median

    if best_inliers is None:
        raise ValueError("RANSAC line fitting failed")

    required_inliers = max(min_points, int(math.ceil(len(points) * min_inlier_ratio)))
    if best_count < required_inliers:
        raise ValueError(
            "Not enough RANSAC inliers: "
            f"{best_count}/{len(points)}, need >= {required_inliers}"
        )

    inlier_points = points[best_inliers]
    line_point, line_direction = fit_line_tls(inlier_points)
    residuals = line_residuals(inlier_points, line_point, line_direction)
    diagnostics = {
        "support_count": int(len(points)),
        "inlier_count": int(len(inlier_points)),
        "outlier_count": int(len(points) - len(inlier_points)),
        "inlier_ratio": float(len(inlier_points) / len(points)),
        "residual_threshold_mm": float(residual_threshold_mm),
        "residuals": summarize_residuals(residuals),
    }
    return line_point, line_direction, inlier_points, diagnostics


def intersect_lines(point_a, direction_a, point_b, direction_b):
    matrix = np.column_stack((direction_a, -direction_b))
    det = float(np.linalg.det(matrix))
    if abs(det) <= 1e-9:
        raise ValueError("Fitted LiDAR target sides are nearly parallel")
    params = np.linalg.solve(matrix, point_b - point_a)
    return point_a + params[0] * direction_a


def project_point_to_line(point, line_point, line_direction):
    return line_point + np.dot(point - line_point, line_direction) * line_direction


def line_segment_for_display(points, line_point, line_direction):
    if len(points) == 0:
        return None
    projections = (points - line_point) @ line_direction
    start = line_point + projections.min() * line_direction
    end = line_point + projections.max() * line_direction
    return {
        "start": {"x_mm": float(start[0]), "z_mm": float(start[1])},
        "end": {"x_mm": float(end[0]), "z_mm": float(end[1])},
    }


def points_for_display(points):
    return [
        {
            "x_mm": float(point[0]),
            "z_mm": float(point[1]),
        }
        for point in points
    ]


def make_feature(feature_id, role, point_xz, source):
    x_mm = float(point_xz[0])
    z_mm = float(point_xz[1])
    angle_deg, distance_mm = cartesian_to_polar(x_mm, z_mm)
    return {
        "id": int(feature_id),
        "role": role,
        "source": source,
        "angle_deg": float(angle_deg),
        "distance_mm": float(distance_mm),
        "x_mm": x_mm,
        "y_mm": 0.0,
        "z_mm": z_mm,
    }


def extract_corner_features(
    scan_data,
    manual_clicks,
    threshold_mm=CORNER_FIT_DISTANCE_THRESHOLD_MM,
    min_points_per_side=CORNER_FIT_MIN_POINTS_PER_SIDE,
    ransac_residual_threshold_mm=CORNER_RANSAC_RESIDUAL_THRESHOLD_MM,
    ransac_min_inlier_ratio=CORNER_RANSAC_MIN_INLIER_RATIO,
):
    if len(manual_clicks) != 3:
        raise ValueError("Exactly 3 LiDAR guide clicks are required")

    scan_points = scan_to_xz_points(scan_data)
    if len(scan_points) < min_points_per_side * 2:
        raise ValueError(f"Not enough LiDAR points in snapshot: {len(scan_points)}")

    click_points = np.array(
        [[float(item["x_mm"]), float(item["z_mm"])] for item in manual_clicks],
        dtype=np.float64,
    )

    left_points = select_points_near_segment(scan_points, click_points[0], click_points[1], threshold_mm)
    right_points = select_points_near_segment(scan_points, click_points[1], click_points[2], threshold_mm)

    if len(left_points) < min_points_per_side or len(right_points) < min_points_per_side:
        raise ValueError(
            "Not enough LiDAR support points near target sides: "
            f"left={len(left_points)}, right={len(right_points)}, "
            f"need >= {min_points_per_side} each"
        )

    left_line_point, left_line_direction, left_inliers, left_fit = fit_line_ransac_then_tls(
        left_points,
        ransac_residual_threshold_mm,
        min_points_per_side,
        ransac_min_inlier_ratio,
    )
    right_line_point, right_line_direction, right_inliers, right_fit = fit_line_ransac_then_tls(
        right_points,
        ransac_residual_threshold_mm,
        min_points_per_side,
        ransac_min_inlier_ratio,
    )
    center = intersect_lines(left_line_point, left_line_direction, right_line_point, right_line_direction)
    left_feature = project_point_to_line(click_points[0], left_line_point, left_line_direction)
    right_feature = project_point_to_line(click_points[2], right_line_point, right_line_direction)

    features = [
        make_feature(1, "left_edge_feature", left_feature, "manual_click_projected_to_left_ransac_tls_line"),
        make_feature(2, "corner_intersection_feature", center, "intersection_of_left_and_right_ransac_tls_lines"),
        make_feature(3, "right_edge_feature", right_feature, "manual_click_projected_to_right_ransac_tls_line"),
    ]

    diagnostics = {
        "method": "guided_v_shape_ransac_tls_fit",
        "threshold_mm": float(threshold_mm),
        "min_points_per_side": int(min_points_per_side),
        "ransac_residual_threshold_mm": float(ransac_residual_threshold_mm),
        "ransac_min_inlier_ratio": float(ransac_min_inlier_ratio),
        "input_scan_points": int(len(scan_points)),
        "left_support_count": int(len(left_points)),
        "right_support_count": int(len(right_points)),
        "left_inlier_count": int(len(left_inliers)),
        "right_inlier_count": int(len(right_inliers)),
        "left_line_fit": left_fit,
        "right_line_fit": right_fit,
        "left_support_points": points_for_display(left_points),
        "right_support_points": points_for_display(right_points),
        "left_inlier_points": points_for_display(left_inliers),
        "right_inlier_points": points_for_display(right_inliers),
        "left_line": line_segment_for_display(left_inliers, left_line_point, left_line_direction),
        "right_line": line_segment_for_display(right_inliers, right_line_point, right_line_direction),
    }
    return features, diagnostics
