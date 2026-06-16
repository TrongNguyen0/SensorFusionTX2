# 05 - Fusion Validation Upgrade

## Muc tieu
Nang fusion_calibration.py tu muc ve diem LiDAR len anh thanh buoc validation co UI, sparse LiDAR depth va so sanh voi RealSense depth.

## Da sua trong src/fusion_calibration.py
1. Tach code thanh cac ham ro rang:
   - load_calibration.
   - init_realsense.
   - init_lidar.
   - scan_to_lidar_points.
   - project_lidar_points.
   - process_scan.
   - save_frame.
   - main.

2. Tuong thich nguoc voi calibration_result_pnp.npz cu:
   - Neu file chua co distCoeffs thi dung zeros va in warning.
   - Neu file chua co rvec/tvec thi tinh rvec tu R va dung T lam tvec.

3. Dung cv2.projectPoints de project diem LiDAR:
   - Ho tro dung distortion coefficients khi compute moi da luu distCoeffs.
   - Giam sai lech so voi cach tinh u, v thu cong.

4. Sua don vi sparse depth:
   - Zc tu calibration dang cung don vi voi LiDAR, tuc mm.
   - Khong nhan Zc * 1000 nua.
   - Luu sparse depth bang uint16 theo mm.

5. Tao validation metrics moi frame:
   - raw_lidar_points.
   - front_lidar_points.
   - projected_points.
   - valid_depth_pairs.
   - depth_error_mm: mean, median, max, std.

6. So sanh depth LiDAR voi RealSense depth:
   - Lay depth_scale tu RealSense depth sensor.
   - RealSense depth mm = raw_depth * depth_scale * 1000.
   - Depth error = abs(lidar_depth_mm - realsense_depth_mm).

7. UI validation 2x2:
   - RGB + LiDAR overlay.
   - RealSense depth colormap.
   - Sparse LiDAR depth colormap.
   - Metrics/status panel.

8. Luu ket qua khi nhan S:
   - data/fusion_output/rgb/*.png.
   - data/fusion_output/depth_dense/*.png.
   - data/fusion_output/depth_sparse/*.png.
   - data/fusion_output/fusion/*.png.
   - data/fusion_output/metrics/*.json.

9. Cleanup an toan:
   - Neu khoi tao loi giua chung, chi dong tai nguyen da mo.
   - Dong lidar/pipeline trong try/except rieng.

## Kiem chung da chay
1. Syntax check:
   python -m py_compile src/fusion_calibration.py
   Ket qua: pass.

2. Non-hardware smoke test:
   - Load calibration_result_pnp.npz hien tai.
   - File calibration cu chi co K, R, T nen code fallback distCoeffs = 0.
   - Project scan gia va tinh metrics.
   - Ket qua: sparse_nonzero = 2, metrics sinh dung cau truc.

## Chua kiem chung duoc
Chua chay validation realtime voi RealSense va RPLidar thuc te. Can chay:
python src/fusion_calibration.py

## Luu y khoa hoc
Depth comparison chi co y nghia tai cac pixel co ca diem LiDAR project hop le va RealSense depth khac 0. Neu valid_depth_pairs thap, khong nen ket luan manh ve sai so depth.

## Buoc tiep theo de xuat
1. Chay collect voi hardware va thu sample moi neu can.
2. Chay compute de tao calibration_result_pnp.npz moi co distCoeffs/rvec/tvec/metrics.
3. Chay fusion validation, luu anh va metrics.
4. Dua so lieu that vao README va bao cao.
