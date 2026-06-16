# 04 - Compute Calibration Upgrade

## Muc tieu
Nang compute_calibration.py tu script chi tinh K/R/T thanh buoc calibration co danh gia dinh luong va output phuc vu bao cao.

## Da sua trong src/compute_calibration.py
1. Them thu muc output rieng:
   - data/calibration_result/calibration_metrics.json
   - data/calibration_result/reprojection_preview/

2. Them preflight RealSense:
   - Kiem tra co RealSense hay khong truoc khi pipeline.start.
   - In ten/serial/firmware neu doc duoc.
   - Bao loi ro rang neu khong co camera.

3. Load data chat che hon:
   - Duyet tat ca pair_*.json.
   - Bo qua mapped point thieu field bat buoc.
   - Luu records theo tung diem de tao point_report va anh preview.
   - Kiem tra so correspondence toi thieu.

4. Giu cong thuc toa do LiDAR hien tai:
   - x = distance * sin(angle).
   - z = distance * cos(angle).
   - P_L = [x, 0, z].

5. Nang solvePnPRansac:
   - Luu rvec, tvec, R, T.
   - Luu inlier_indices.
   - In inlier/total.

6. Tinh sai so tai chieu cho ca all points va inliers:
   - mean.
   - median.
   - max.
   - std.
   - inlier_ratio.

7. Luu calibration_result_pnp.npz day du hon:
   - K.
   - distCoeffs.
   - rvec.
   - tvec.
   - R.
   - T.
   - inlier_indices.
   - projected_points.
   - reprojection_errors.

8. Luu calibration_metrics.json:
   - camera_info.
   - camera_intrinsics.
   - ransac_config.
   - extrinsics.
   - metrics.
   - file_stats.
   - preview_images.
   - point_report theo tung correspondence.

9. Tao reprojection preview images:
   - Mau xanh duong: observed pixel.
   - Mau xanh la: projected inlier.
   - Mau do: projected outlier.
   - Duong vang: sai lech tu observed den projected.

## Kiem chung da chay
1. Syntax check:
   python -m py_compile src/compute_calibration.py
   Ket qua: pass.

2. Non-hardware load_data smoke test:
   - Loaded 19 pair files.
   - Loaded 304 valid correspondences.
   - Ket qua: pass.

## Chua chay
Chua chay main compute that vi can RealSense ket noi de doc intrinsics. Khi camera da ket noi, chay:
python src/compute_calibration.py

## Output ky vong sau khi chay main
- calibration_result_pnp.npz o root project.
- data/calibration_result/calibration_metrics.json.
- data/calibration_result/reprojection_preview/*.png.
- Terminal in K, distCoeffs, R, T va reprojection metrics.

## Y nghia khoa hoc
Buoc compute bay gio co the tra loi:
- Co bao nhieu file calibration duoc dung?
- Tong so correspondence la bao nhieu?
- Bao nhieu diem la inlier/outlier?
- Sai so tai chieu trung binh/trung vi/lon nhat/do lech chuan la bao nhieu?
- Diem project lai co khop diem quan sat tren anh hay khong?

## Buoc tiep theo de xuat
Chuyen sang fusion_calibration.py:
- Doc distCoeffs/rvec/tvec neu co.
- Dung cv2.projectPoints de project diem LiDAR.
- Tao RGB overlay.
- Tao sparse LiDAR depth map.
- So sanh depth LiDAR voi RealSense depth tai pixel hop le.
- Luu metrics validation.
