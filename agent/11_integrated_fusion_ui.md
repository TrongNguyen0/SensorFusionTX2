# 11 - Integrated Fusion UI

## Yeu cau
Khong muon Fusion mo mot cua so OpenCV rieng. Fusion phai hien truc tiep trong PyQt UI giong tinh than Collect: vung hien thi ben trai, nut dieu khien ben phai, va co nut save frame trong UI.

## Da sua
### 1. Them core/fusion_core.py
Tach logic fusion de UI goi truc tiep:
- load_calibration.
- scan_to_lidar_points.
- project_lidar_points.
- process_scan.
- render_dense_depth.
- render_sparse_depth.
- metrics_to_text.
- save_fusion_frame.

### 2. Them FusionWorker trong app_pyqt.py
FusionWorker chay trong QThread:
- Load calibration_result_pnp.npz.
- Khoi tao RealSense.
- Lay depth_scale.
- Khoi tao RPLidar.
- Doc scan va frame realtime.
- Project LiDAR len RGB.
- Tao sparse depth.
- Tinh depth metrics.
- Emit frame/metrics ve UI.

### 3. Sua Fusion tab
Thay log-only view bang layout 2x2:
- RGB + LiDAR overlay.
- RealSense depth colormap.
- Sparse LiDAR depth.
- Metrics text view.

### 4. Sua Fusion controls
Thay Launch Fusion Validation bang:
- Start Fusion.
- Stop Fusion.
- Save Frame.

Save Frame luu:
- data/fusion_output/rgb/*.png.
- data/fusion_output/depth_dense/*.png.
- data/fusion_output/depth_sparse/*.png.
- data/fusion_output/fusion/*.png.
- data/fusion_output/metrics/*.json.

## Log Fusion hien o dau
Co hai loai log:

1. Metrics realtime cua Fusion
Hien trong o duoi-phai cua tab Fusion, gom:
- raw_lidar_points.
- front_lidar_points.
- projected_points.
- valid_depth_pairs.
- depth_error mean/median/max/std.

2. Log su kien/trang thai
Hien trong log panel ben phai cua UI, gom:
- Fusion calibration loaded.
- Fusion sensors started.
- Fusion error neu co.
- Fusion stopped.
- Duong dan metrics khi Save Frame.

## Diem can luu y
- Khi Start Fusion, neu Collect sensors dang chay thi UI se stop collect sensors truoc de tranh tranh RealSense/LiDAR.
- fusion_calibration.py CLI van duoc giu lai lam backup, nhung UI khong con goi no de mo cua so rieng.
- FusionWorker.stop hien wait toi 3 giay; neu hardware block co the can tinh chinh sau test that.

## Kiem chung
Da chay:
python -m py_compile src/app_pyqt.py src/core/fusion_core.py

Da chay import smoke test:
import app_pyqt; import core.fusion_core

Ket qua: pass.

## Chua kiem chung
Chua test realtime voi hardware trong UI. Can chay:
python src/app_pyqt.py

Sau do vao Fusion tab:
1. Bam Start Fusion.
2. Kiem tra 3 vung anh co cap nhat khong.
3. Kiem tra metrics realtime.
4. Bam Save Frame va xem data/fusion_output/metrics.
5. Bam Stop Fusion.
