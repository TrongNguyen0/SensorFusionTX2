"""
LiDAR-Camera Calibration Computation (Homography)
===================================================
Tính ma trận Homography H (3x3) chuyển đổi tọa độ LiDAR → pixel camera.

Pipeline:
1. Load các file JSON calibration từ captured_data/calibration/
2. Chuyển LiDAR polar (angle, distance) → Cartesian (x, z):
   - x = distance * sin(angle)   (trục ngang)
   - z = distance * cos(angle)   (trục sâu)
3. Dùng cv2.findHomography() tìm H sao cho:
   [u, v, 1]^T = H @ [x, z, 1]^T

Yêu cầu: ít nhất 4 cặp điểm LiDAR ↔ Pixel
"""

import numpy as np
import cv2
import json
import os
import glob
import sys
import pyrealsense2 as rs

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CALIBRATION_DIR = os.path.join(PROJECT_ROOT, "data", "captured_data", "calibration")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "calibration_result.npz")


def load_calibration_jsons(calibration_dir):
    """Load tất cả file JSON calibration và gom các cặp điểm."""
    json_files = sorted(glob.glob(os.path.join(calibration_dir, "calibration_*.json")))

    if len(json_files) == 0:
        print(f"Không tìm thấy file calibration trong '{calibration_dir}'!")
        print("Chạy 'python collect_calibration.py' trước để thu thập dữ liệu.")
        sys.exit(1)

    all_lidar_points = []  # (x, z) in mm
    all_pixel_points = []  # (u, v)

    print(f"Tìm thấy {len(json_files)} file calibration:")

    for jf in json_files:
        with open(jf, 'r') as f:
            data = json.load(f)

        mapped = data.get('mapped_points', [])

        print(f"  - {os.path.basename(jf)}: {len(mapped)} điểm")

        for pt in mapped:
            angle_rad = np.radians(pt['angle'])
            distance_mm = pt['distance']

            x = distance_mm * np.sin(angle_rad)
            z = distance_mm * np.cos(angle_rad)

            all_lidar_points.append([x, z])
            all_pixel_points.append([pt['pixel_x'], pt['pixel_y']])

    lidar_pts = np.array(all_lidar_points, dtype=np.float64)
    pixel_pts = np.array(all_pixel_points, dtype=np.float64)

    print(f"\nTổng cộng: {len(lidar_pts)} cặp điểm LiDAR ↔ Pixel")
    return lidar_pts, pixel_pts


def compute_homography(lidar_pts, pixel_pts):
    """Tính Homography H (3x3) từ LiDAR Cartesian → Pixel."""
    print("\n" + "=" * 50)
    print("  HOMOGRAPHY (2D → 2D)")
    print("=" * 50)

    if len(lidar_pts) < 4:
        print(f"Cần ít nhất 4 cặp điểm! Hiện có: {len(lidar_pts)}")
        sys.exit(1)

    H, mask = cv2.findHomography(lidar_pts, pixel_pts, cv2.RANSAC, 5.0)

    if H is None:
        print("Không tìm được Homography!")
        sys.exit(1)

    inliers = mask.ravel().sum()
    total = len(mask)
    print(f"  Inliers: {inliers}/{total} ({100 * inliers / total:.1f}%)")
    print(f"\n  Homography Matrix H (3x3):")
    print(f"  {H}")

    # Reprojection error
    lidar_h = np.hstack([lidar_pts, np.ones((len(lidar_pts), 1))])
    projected = (H @ lidar_h.T).T #Nhân H: projected = H × [x, z, 1]^T
    projected = projected[:, :2] / projected[:, 2:3]

    errors = np.linalg.norm(projected - pixel_pts, axis=1)

    print(f"\n  Reprojection Error:")
    print(f"    Mean:   {errors.mean():.2f} px")
    print(f"    Median: {np.median(errors):.2f} px")
    print(f"    Max:    {errors.max():.2f} px")
    print(f"    Std:    {errors.std():.2f} px")

    return H, errors


def visualize_results(lidar_pts, pixel_pts, H, calibration_dir):
    """Hiển thị kết quả calibration trên ảnh."""
    img_files = sorted(glob.glob(os.path.join(calibration_dir, "*.png")))
    if img_files:
        img = cv2.imread(img_files[-1])
    else:
        img = np.zeros((480, 640, 3), dtype=np.uint8)

    result_img = img.copy()

    # Pixel points gốc (xanh lá)
    for px, py in pixel_pts.astype(int):
        cv2.circle(result_img, (px, py), 5, (0, 255, 0), -1)

    # Projected points từ Homography (đỏ)
    lidar_h = np.hstack([lidar_pts, np.ones((len(lidar_pts), 1))])
    projected = (H @ lidar_h.T).T
    projected = projected[:, :2] / projected[:, 2:3]

    for px, py in projected.astype(int):
        cv2.circle(result_img, (px, py), 3, (0, 0, 255), -1)

    cv2.putText(result_img, "Green: Ground truth | Red: Homography",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    cv2.imshow("Calibration Result", result_img)
    print("\nNhấn phím bất kỳ để đóng...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def main():
    print("=" * 50)
    print("  LiDAR-Camera Calibration (Homography)")
    print("=" * 50)

    # 1. Load dữ liệu
    lidar_pts, pixel_pts = load_calibration_jsons(CALIBRATION_DIR)

    if len(lidar_pts) < 4:
        print(f"\nKhông đủ điểm! Cần ít nhất 4 cặp, hiện có {len(lidar_pts)}.")
        print("Chạy 'python collect_calibration.py' để thu thập thêm dữ liệu.")
        sys.exit(1)

    # 2. Tính Homography
    H, errors = compute_homography(lidar_pts, pixel_pts)

    # 3. Lưu kết quả
    np.savez(OUTPUT_FILE,
             homography=H,
             homography_error=errors.mean(),
             num_points=len(lidar_pts))
    print(f"\n  Đã lưu kết quả → {OUTPUT_FILE}")

    # 4. Hiển thị
    visualize_results(lidar_pts, pixel_pts, H, CALIBRATION_DIR)

    # 5. Hướng dẫn sử dụng
    print("\n" + "=" * 50)
    print("  CÁCH SỬ DỤNG")
    print("=" * 50)
    print(f"""
  Load kết quả:
    data = np.load('{OUTPUT_FILE}')
    H = data['homography']

  Chuyển đổi LiDAR → Pixel:
    angle_rad = np.radians(angle_deg)
    x = distance * np.sin(angle_rad)
    z = distance * np.cos(angle_rad)

    pt = np.array([x, z, 1.0])
    pixel = H @ pt
    u, v = pixel[:2] / pixel[2]
""")


if __name__ == "__main__":
    main()
