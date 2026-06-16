import math
import statistics


FRONT_ANGLE_MIN = -90
FRONT_ANGLE_MAX = 90
DENOISE_SCAN_COUNT = 10
ANGLE_BIN_DEG = 1
BAR_DISTANCE_JUMP_THRESHOLD_MM = 300


def normalize_angle(angle_deg):
    if angle_deg > 180:
        return angle_deg - 360
    return angle_deg


def polar_to_cartesian(angle_deg, distance_mm):
    angle_rad = math.radians(angle_deg)
    x = distance_mm * math.sin(angle_rad)
    z = distance_mm * math.cos(angle_rad)
    return x, z


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


def angle_bin(angle, angle_bin_deg=ANGLE_BIN_DEG):
    return round(angle / angle_bin_deg) * angle_bin_deg


def analyze_denoise_bins(scans, denoised_points, angle_bin_deg=ANGLE_BIN_DEG):
    if not scans:
        return {
            "current_bins": 0,
            "stale_bins": 0,
            "max_bin_age": None,
            "point_ages": [],
        }

    latest_scan = scans[-1]
    current_bins = {
        angle_bin(angle, angle_bin_deg)
        for _, angle, distance in latest_scan
        if distance > 0
    }

    bin_age = {}
    for age, scan in enumerate(reversed(scans)):
        for _, angle, distance in scan:
            if distance <= 0:
                continue
            binned_angle = angle_bin(angle, angle_bin_deg)
            if binned_angle not in bin_age:
                bin_age[binned_angle] = age

    point_ages = []
    stale_bins = 0
    max_bin_age = 0
    for _, angle, distance in denoised_points:
        binned_angle = angle_bin(angle, angle_bin_deg)
        age = bin_age.get(binned_angle)
        point_ages.append(age)
        if age is not None:
            max_bin_age = max(max_bin_age, age)
        if binned_angle not in current_bins:
            stale_bins += 1

    return {
        "current_bins": len(current_bins),
        "stale_bins": stale_bins,
        "max_bin_age": max_bin_age if point_ages else None,
        "point_ages": point_ages,
    }


def extract_bar_points(scan_data, angle_a, angle_b, jump_threshold_mm=BAR_DISTANCE_JUMP_THRESHOLD_MM):
    start = min(angle_a, angle_b)
    end = max(angle_a, angle_b)
    bar = [(q, a, d) for q, a, d in scan_data if start <= a <= end]
    bar.sort(key=lambda item: item[1])

    clean_bar = []
    prev_dist = None
    for q, angle, distance in bar:
        if prev_dist is None or abs(distance - prev_dist) < jump_threshold_mm:
            clean_bar.append((q, angle, distance))
            prev_dist = distance
    return clean_bar


def nearest_lidar_point(scan_data, x_query, z_query):
    if not scan_data:
        return None

    best = None
    best_dist_sq = float("inf")
    for point in scan_data:
        _, angle, distance = point
        x, z = polar_to_cartesian(angle, distance)
        dx = x - x_query
        dz = z - z_query
        dist_sq = dx * dx + dz * dz
        if dist_sq < best_dist_sq:
            best_dist_sq = dist_sq
            best = point
    return best
