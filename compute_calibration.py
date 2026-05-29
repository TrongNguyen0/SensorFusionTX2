import numpy as np
import cv2
import json
import os
import glob
import pyrealsense2 as rs
import time

# ==============================
# CONFIG
# ==============================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALIBRATION_DIR = os.path.join(PROJECT_ROOT, "data", "captured_data", "pair")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "calibration_result_pnp.npz")

# ==============================
# CAMERA INTRINSICS
# ==============================
def get_camera_intrinsics():
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    profile = pipeline.start(config)
    time.sleep(1)

    intr = profile.get_stream(rs.stream.color).as_video_stream_profile().get_intrinsics()
    pipeline.stop()

    K = np.array([
        [intr.fx, 0, intr.ppx],
        [0, intr.fy, intr.ppy],
        [0, 0, 1]
    ], dtype=np.float64)

    distCoeffs = np.array(intr.coeffs)

    print("Camera Intrinsics:")
    print(K)
    print("Distortion:", distCoeffs)

    return K, distCoeffs

# ==============================
# LOAD DATA
# ==============================
def load_data():
    json_files = sorted(glob.glob(os.path.join(CALIBRATION_DIR, "pair_*.json")))

    lidar_pts = []
    pixel_pts = []

    for jf in json_files:
        with open(jf, 'r') as f:
            data = json.load(f)

        for pt in data['mapped_points']:
            angle = np.radians(pt['angle'])
            dist = pt['distance']

            x = dist * np.sin(angle)
            z = dist * np.cos(angle)

            lidar_pts.append([x, 0, z])
            pixel_pts.append([pt['pixel_x'], pt['pixel_y']])

    lidar_pts = np.array(lidar_pts, dtype=np.float64)
    pixel_pts = np.array(pixel_pts, dtype=np.float64)

    print(f"Loaded {len(lidar_pts)} correspondences")

    return lidar_pts, pixel_pts

# ==============================
# PNP + RANSAC
# ==============================
def solve_pnp(lidar_pts, pixel_pts, K, distCoeffs):

    success, rvec, tvec, inliers = cv2.solvePnPRansac(
        lidar_pts,
        pixel_pts,
        K,
        distCoeffs,
        flags=cv2.SOLVEPNP_IPPE,
        iterationsCount=1000,
        reprojectionError=8.0,
        confidence=0.99
    )

    if not success:
        raise RuntimeError("PnP failed")

    R, _ = cv2.Rodrigues(rvec)
    T = tvec.reshape(3, 1)

    print(f"Inliers: {len(inliers)}/{len(lidar_pts)}")

    return R, T, inliers

# ==============================
# ERROR
# ==============================
def compute_error(lidar_pts, pixel_pts, R, T, K, distCoeffs, inliers):

    lidar_in = lidar_pts[inliers.flatten()]
    pixel_in = pixel_pts[inliers.flatten()]

    proj, _ = cv2.projectPoints(lidar_in, cv2.Rodrigues(R)[0], T, K, distCoeffs)
    proj = proj.reshape(-1, 2)

    errors = np.linalg.norm(proj - pixel_in, axis=1)

    print("Reprojection Error:")
    print(f"Mean: {errors.mean():.2f} px")
    print(f"Median: {np.median(errors):.2f} px")
    print(f"Max: {errors.max():.2f} px")

    return errors

# ==============================
# MAIN
# ==============================
def main():

    K, distCoeffs = get_camera_intrinsics()
    lidar_pts, pixel_pts = load_data()

    R, T, inliers = solve_pnp(lidar_pts, pixel_pts, K, distCoeffs)

    compute_error(lidar_pts, pixel_pts, R, T, K, distCoeffs, inliers)

    np.savez(OUTPUT_FILE,
             K=K,
             R=R,
             T=T)

    print("\nSaved:", OUTPUT_FILE)
    print("\n==K = \n", K)
    print("\n==R = \n", R)
    print("\n==T = \n", T)
    print("\n=== USE ===")
    print("camera = R @ lidar + T")
    print("pixel = K @ camera")


if __name__ == "__main__":
    main()
