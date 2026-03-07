"""
LiDAR-Camera Calibration Computation
=====================================
Tính ma trận chuyển đổi từ tọa độ LiDAR (angle, distance) sang tọa độ pixel camera.

Phương pháp:
1. Chuyển LiDAR polar (angle, distance) → Cartesian (x, z) trong mặt phẳng quét
   - x = distance * sin(angle)   (trục ngang, phải là dương)
   - z = distance * cos(angle)   (trục sâu, phía trước là dương)

2. Dùng cv2.findHomography() để tìm ma trận H (3x3) ánh xạ:
   [u, v, 1]^T = H @ [x_lidar, z_lidar, 1]^T
   
   Hoặc dùng cv2.solvePnP() nếu có camera intrinsics để tìm [R|T] extrinsic.

Yêu cầu:
- Cần ít nhất 4 cặp điểm (tốt nhất thu nhiều lần ở các vị trí/khoảng cách khác nhau)
- Các file JSON calibration nằm trong captured_data/calibration/
"""

import numpy as np
import cv2
import json
import os
import glob
import sys
import pyrealsense2 as rs

CALIBRATION_DIR = "captured_data/calibration"
OUTPUT_FILE = "calibration_result.npz"


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
        timestamp = data.get('timestamp', '?')
        
        print(f"  - {os.path.basename(jf)}: {len(mapped)} điểm")
        
        for pt in mapped:
            angle_deg = pt['angle']
            distance_mm = pt['distance']
            px = pt['pixel_x']
            py = pt['pixel_y']
            
            # Convert polar → Cartesian (mm)
            angle_rad = np.radians(angle_deg)
            x = distance_mm * np.sin(angle_rad)   # trục ngang
            z = distance_mm * np.cos(angle_rad)    # trục sâu (phía trước)
            
            all_lidar_points.append([x, z])
            all_pixel_points.append([px, py])
    
    lidar_pts = np.array(all_lidar_points, dtype=np.float64)
    pixel_pts = np.array(all_pixel_points, dtype=np.float64)
    
    print(f"\nTổng cộng: {len(lidar_pts)} cặp điểm LiDAR ↔ Pixel")
    return lidar_pts, pixel_pts


def get_realsense_intrinsics():
    """Lấy camera intrinsics từ RealSense (nếu có kết nối)."""
    try:
        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        profile = pipeline.start(config)
        
        # Lấy intrinsics
        color_stream = profile.get_stream(rs.stream.color)
        intrinsics = color_stream.as_video_stream_profile().get_intrinsics()
        
        K = np.array([
            [intrinsics.fx, 0, intrinsics.ppx],
            [0, intrinsics.fy, intrinsics.ppy],
            [0, 0, 1]
        ], dtype=np.float64)
        
        dist_coeffs = np.array(intrinsics.coeffs, dtype=np.float64)
        
        pipeline.stop()
        
        print(f"\nCamera Intrinsics (từ RealSense):")
        print(f"  fx={intrinsics.fx:.1f}, fy={intrinsics.fy:.1f}")
        print(f"  cx={intrinsics.ppx:.1f}, cy={intrinsics.ppy:.1f}")
        print(f"  Distortion: {dist_coeffs}")
        
        return K, dist_coeffs
    
    except Exception as e:
        print(f"\nKhông kết nối được RealSense: {e}")
        print("Sử dụng intrinsics mặc định cho D435 (640x480)")
        
        # Default D435 intrinsics for 640x480
        K = np.array([
            [615.0, 0, 320.0],
            [0, 615.0, 240.0],
            [0, 0, 1]
        ], dtype=np.float64)
        dist_coeffs = np.zeros(5, dtype=np.float64)
        
        return K, dist_coeffs


def method_homography(lidar_pts, pixel_pts):
    """
    Phương pháp 1: Homography 2D → 2D
    Tìm ma trận H (3x3) sao cho: pixel = H @ lidar_homogeneous
    
    Ưu điểm: Đơn giản, chỉ cần 4+ cặp điểm
    Nhược điểm: Không tách riêng được R, T, K
    """
    print("\n" + "="*50)
    print("PHƯƠNG PHÁP 1: HOMOGRAPHY (2D → 2D)")
    print("="*50)
    
    if len(lidar_pts) < 4:
        print(f"Cần ít nhất 4 cặp điểm! Hiện có: {len(lidar_pts)}")
        print("Thu thập thêm dữ liệu calibration ở các vị trí/khoảng cách khác nhau.")
        return None, None
    
    H, mask = cv2.findHomography(lidar_pts, pixel_pts, cv2.RANSAC, 5.0)
    
    if H is None:
        print("Không tìm được Homography!")
        return None, None
    
    inliers = mask.ravel().sum()
    total = len(mask)
    print(f"  Inliers: {inliers}/{total} ({100*inliers/total:.1f}%)")
    print(f"\n  Homography Matrix H (3x3):")
    print(f"  {H}")
    
    # Tính reprojection error
    lidar_h = np.hstack([lidar_pts, np.ones((len(lidar_pts), 1))])  # Nx3
    projected = (H @ lidar_h.T).T  # Nx3
    projected = projected[:, :2] / projected[:, 2:3]  # Normalize
    
    errors = np.linalg.norm(projected - pixel_pts, axis=1)
    
    print(f"\n  Reprojection Error:")
    print(f"    Mean:   {errors.mean():.2f} px")
    print(f"    Median: {np.median(errors):.2f} px")
    print(f"    Max:    {errors.max():.2f} px")
    print(f"    Std:    {errors.std():.2f} px")
    
    return H, errors


def method_solvepnp(lidar_pts, pixel_pts, K, dist_coeffs):
    """
    Phương pháp 2: solvePnP (3D → 2D projection)
    Coi LiDAR là điểm 3D: [x, 0, z] (y=0 vì LiDAR 2D nằm ngang)
    Tìm R, T extrinsic sao cho: pixel = K @ (R @ P_lidar + T)
    
    Ưu điểm: Tách riêng được R, T, dùng được camera intrinsics
    Nhược điểm: Cần nhiều điểm không cùng nằm trên 1 đường thẳng
    """
    print("\n" + "="*50)
    print("PHƯƠNG PHÁP 2: solvePnP (3D → 2D)")
    print("="*50)
    
    if len(lidar_pts) < 4:
        print(f"Cần ít nhất 4 cặp điểm! Hiện có: {len(lidar_pts)}")
        return None, None, None
    
    # LiDAR 2D → 3D: [x, 0, z] (y=0, quét ngang)
    # Chuyển sang mét
    lidar_3d = np.zeros((len(lidar_pts), 3), dtype=np.float64)
    lidar_3d[:, 0] = lidar_pts[:, 0] / 1000.0  # x (mm → m)
    lidar_3d[:, 1] = 0.0                         # y = 0 (LiDAR 2D)
    lidar_3d[:, 2] = lidar_pts[:, 1] / 1000.0  # z (mm → m)
    
    pixel_2d = pixel_pts.astype(np.float64)
    
    # Thử nhiều method
    methods = [
        ("SOLVEPNP_ITERATIVE", cv2.SOLVEPNP_ITERATIVE),
        ("SOLVEPNP_SQPNP", cv2.SOLVEPNP_SQPNP),
    ]
    
    best_rvec, best_tvec = None, None
    best_error = float('inf')
    
    for name, method in methods:
        try:
            success, rvec, tvec = cv2.solvePnP(
                lidar_3d, pixel_2d, K, dist_coeffs, flags=method
            )
            
            if not success:
                continue
            
            # Reprojection error
            projected, _ = cv2.projectPoints(lidar_3d, rvec, tvec, K, dist_coeffs)
            projected = projected.reshape(-1, 2)
            errors = np.linalg.norm(projected - pixel_2d, axis=1)
            mean_err = errors.mean()
            
            print(f"  {name}: mean_error = {mean_err:.2f} px")
            
            if mean_err < best_error:
                best_error = mean_err
                best_rvec = rvec
                best_tvec = tvec
        except Exception as e:
            print(f"  {name}: Lỗi - {e}")
    
    if best_rvec is None:
        print("  Không tìm được nghiệm solvePnP!")
        print("  Tip: Cần thu thập dữ liệu ở nhiều khoảng cách/vị trí khác nhau.")
        return None, None, None
    
    R, _ = cv2.Rodrigues(best_rvec)
    T = best_tvec.flatten()
    
    print(f"\n  Rotation Matrix R:")
    print(f"  {R}")
    print(f"\n  Translation Vector T (m):")
    print(f"  {T}")
    
    # Reprojection error chi tiết
    projected, _ = cv2.projectPoints(lidar_3d, best_rvec, best_tvec, K, dist_coeffs)
    projected = projected.reshape(-1, 2)
    errors = np.linalg.norm(projected - pixel_2d, axis=1)
    
    print(f"\n  Reprojection Error:")
    print(f"    Mean:   {errors.mean():.2f} px")
    print(f"    Median: {np.median(errors):.2f} px")
    print(f"    Max:    {errors.max():.2f} px")
    
    return R, T, errors


def method_affine(lidar_pts, pixel_pts):
    """
    Phương pháp 3: Affine Transform 2D → 2D
    Tìm ma trận A (2x3) sao cho: pixel = A @ [x, z, 1]^T
    
    Ưu điểm: Ổn định với ít điểm (cần 3+), không bị overfitting
    Nhược điểm: Không mô hình hóa perspective
    """
    print("\n" + "="*50)
    print("PHƯƠNG PHÁP 3: AFFINE TRANSFORM (2D → 2D)")
    print("="*50)
    
    if len(lidar_pts) < 3:
        print(f"Cần ít nhất 3 cặp điểm! Hiện có: {len(lidar_pts)}")
        return None, None
    
    A, inliers = cv2.estimateAffine2D(lidar_pts, pixel_pts, method=cv2.RANSAC)
    
    if A is None:
        print("Không tìm được Affine Transform!")
        return None, None
    
    inlier_count = inliers.ravel().sum()
    total = len(inliers)
    print(f"  Inliers: {inlier_count}/{total} ({100*inlier_count/total:.1f}%)")
    print(f"\n  Affine Matrix A (2x3):")
    print(f"  {A}")
    
    # Reprojection error
    lidar_h = np.hstack([lidar_pts, np.ones((len(lidar_pts), 1))])
    projected = (A @ lidar_h.T).T
    
    errors = np.linalg.norm(projected - pixel_pts, axis=1)
    
    print(f"\n  Reprojection Error:")
    print(f"    Mean:   {errors.mean():.2f} px")
    print(f"    Median: {np.median(errors):.2f} px")
    print(f"    Max:    {errors.max():.2f} px")
    
    return A, errors


def visualize_results(lidar_pts, pixel_pts, H=None, A=None, calibration_dir=None):
    """Hiển thị kết quả calibration trên ảnh."""
    # Tìm ảnh calibration mới nhất
    if calibration_dir:
        img_files = sorted(glob.glob(os.path.join(calibration_dir, "*.png")))
        if img_files:
            img = cv2.imread(img_files[-1])
        else:
            img = np.zeros((480, 640, 3), dtype=np.uint8)
    else:
        img = np.zeros((480, 640, 3), dtype=np.uint8)
    
    result_img = img.copy()
    
    # Vẽ pixel points gốc (xanh lá)
    for px, py in pixel_pts.astype(int):
        cv2.circle(result_img, (px, py), 5, (0, 255, 0), -1)
    
    # Vẽ projected points từ Homography (đỏ)
    if H is not None:
        lidar_h = np.hstack([lidar_pts, np.ones((len(lidar_pts), 1))])
        projected = (H @ lidar_h.T).T
        projected = projected[:, :2] / projected[:, 2:3]
        
        for px, py in projected.astype(int):
            cv2.circle(result_img, (px, py), 3, (0, 0, 255), -1)
        
        cv2.putText(result_img, "Green: Ground truth | Red: Homography", 
                     (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Vẽ projected points từ Affine (vàng)
    if A is not None:
        lidar_h = np.hstack([lidar_pts, np.ones((len(lidar_pts), 1))])
        projected = (A @ lidar_h.T).T
        
        for px, py in projected.astype(int):
            cv2.circle(result_img, (px, py), 3, (0, 255, 255), -1)
        
        y_offset = 50 if H is not None else 30
        cv2.putText(result_img, "Yellow: Affine", 
                     (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    cv2.imshow("Calibration Result", result_img)
    print("\nNhấn phím bất kỳ để đóng...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def main():
    print("="*50)
    print("  LiDAR-Camera Calibration Computation")
    print("="*50)
    
    # 1. Load dữ liệu
    lidar_pts, pixel_pts = load_calibration_jsons(CALIBRATION_DIR)
    
    if len(lidar_pts) < 3:
        print(f"\nKhông đủ điểm! Cần ít nhất 4 cặp, hiện có {len(lidar_pts)}.")
        print("Chạy 'python collect_calibration.py' để thu thập thêm dữ liệu.")
        sys.exit(1)
    
    # 2. Lấy camera intrinsics
    K, dist_coeffs = get_realsense_intrinsics()
    
    # 3. Tính calibration bằng nhiều phương pháp
    H, h_errors = method_homography(lidar_pts, pixel_pts)
    R, T, pnp_errors = method_solvepnp(lidar_pts, pixel_pts, K, dist_coeffs)
    A, a_errors = method_affine(lidar_pts, pixel_pts)
    
    # 4. So sánh và chọn phương pháp tốt nhất
    print("\n" + "="*50)
    print("  SO SÁNH CÁC PHƯƠNG PHÁP")
    print("="*50)
    
    results = {}
    if h_errors is not None:
        results['homography'] = h_errors.mean()
        print(f"  Homography:  {h_errors.mean():.2f} px (mean error)")
    if pnp_errors is not None:
        results['solvepnp'] = pnp_errors.mean()
        print(f"  SolvePnP:    {pnp_errors.mean():.2f} px (mean error)")
    if a_errors is not None:
        results['affine'] = a_errors.mean()
        print(f"  Affine:      {a_errors.mean():.2f} px (mean error)")
    
    if not results:
        print("Không tính được calibration nào!")
        sys.exit(1)
    
    best_method = min(results, key=results.get)
    print(f"\n  >> Phương pháp tốt nhất: {best_method} ({results[best_method]:.2f} px)")
    
    # 5. Lưu kết quả
    save_data = {
        'camera_matrix': K,
        'dist_coeffs': dist_coeffs,
        'best_method': best_method,
        'num_points': len(lidar_pts),
    }
    
    if H is not None:
        save_data['homography'] = H
        save_data['homography_error'] = h_errors.mean()
    if R is not None:
        save_data['rotation'] = R
        save_data['translation'] = T
        save_data['solvepnp_error'] = pnp_errors.mean()
    if A is not None:
        save_data['affine'] = A
        save_data['affine_error'] = a_errors.mean()
    
    np.savez(OUTPUT_FILE, **save_data)
    print(f"\n  Đã lưu kết quả → {OUTPUT_FILE}")
    
    # 6. Hiển thị kết quả
    visualize_results(lidar_pts, pixel_pts, H=H, A=A, calibration_dir=CALIBRATION_DIR)
    
    # 7. Hướng dẫn sử dụng
    print("\n" + "="*50)
    print("  CÁCH SỬ DỤNG")
    print("="*50)
    print(f"""
  Trong code fusion, load kết quả:
    data = np.load('{OUTPUT_FILE}', allow_pickle=True)
    H = data['homography']          # Homography matrix
    
  Chuyển đổi LiDAR → Pixel:
    angle_rad = np.radians(angle_deg)
    x = distance * np.sin(angle_rad)
    z = distance * np.cos(angle_rad)
    
    pt = np.array([x, z, 1.0])
    pixel = H @ pt
    pixel = pixel[:2] / pixel[2]    # (u, v)
    
  Lưu ý: Thu thập thêm dữ liệu ở nhiều khoảng cách/vị trí 
  khác nhau để calibration chính xác hơn!
""")


if __name__ == "__main__":
    main()
