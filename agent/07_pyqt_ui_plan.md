# 07 - PyQt UI Plan

## Muc tieu UI
Xay dung UI kieu calibration tool: mot vung hien thi lon va mot panel thao tac/huong dan. UI phai bao phu collect, compute va fusion, nhung uu tien chi tiet nhat cho collect vi day la buoc tao du lieu calibration.

Tham chieu tinh than tu cac tool ROS/RViz lidar-camera calibration: mot ben la display/visualization, mot ben la control/status/options. Khong dua ROS vao do an; chi ap dung cach to chuc giao dien.

## Bo cuc UI tong the
Main window gom hai vung chinh:

Left Display Area:
- Collect: camera stream/snapshot va LiDAR plot/snapshot.
- Compute: log, metrics, reprojection preview.
- Fusion: RGB overlay, RealSense depth, sparse LiDAR depth.

Right Control Panel:
- Chuyen mode: Collect / Compute / Fusion / Results.
- Nut thao tac.
- Huong dan tung buoc.
- Trang thai thiet bi.
- Metrics va ket qua.

## Cong nghe de xuat
Dung PyQt/PySide cho UI chinh.
Dung pyqtgraph de ve LiDAR plot realtime/snapshot, vi nhe va hop voi PyQt hon Matplotlib.
Dung QLabel hoac QGraphicsView de hien thi anh camera va overlay.
Dung QPlainTextEdit de hien log compute/huong dan.

## Nguyen tac kien truc
Khong nen nhet nguyen 3 script hien tai vao UI. Cac script collect_calibration.py, compute_calibration.py va fusion_calibration.py hien la CLI/script doc lap, co vong lap rieng va co cv2.imshow/plt/keyboard. Neu goi truc tiep trong PyQt main thread, UI de bi treo.

Huong dung: tach logic thanh core modules, UI chi goi core.

Cau truc de xuat:
src/
  app_pyqt.py
  config.py
  core/
    camera_core.py
    lidar_core.py
    collect_core.py
    compute_core.py
    fusion_core.py
  collect_calibration.py
  compute_calibration.py
  fusion_calibration.py

Nguyen tac:
- core khong biet UI la gi.
- UI khong xu ly thuat toan sau.
- UI chi hien thi, nhan thao tac va goi core.
- Giu 3 script CLI hien tai lam backup, khong pha pipeline dang chay.

## Flow Collect UI chi tiet
Collect UI can lam theo mo hinh stream -> capture snapshot -> select -> preview -> accept/reject -> resume.

### 1. Start Sensors
- Khoi tao RealSense.
- Khoi tao RPLidar.
- CameraThread cap nhat latest_color, latest_depth, camera_timestamp.
- LiDARThread cap nhat latest_scan va scans_buffer.
- UI hien camera stream va LiDAR plot realtime.

### 2. Capture Snapshot
Khi nguoi dung bam Capture:
- Copy latest_color.
- Copy latest_depth.
- Copy scans_buffer gan thoi diem bam.
- Dong bang camera display va LiDAR plot.
- Chuyen trang thai UI sang Selecting.

Luu y: camera va LiDAR khong dong bo tuyet doi. Trong pham vi do an, dung latest frame/scan tai thoi diem bam la chap nhan duoc. Neu can tot hon, luu timestamp va chon scan gan nhat camera timestamp.

### 3. Denoise LiDAR Snapshot
Khong dung mot scan don de chon target. Can dung lai logic loc nhieu/lam tron/binning da co trong collect_calibration.py:
1. Loc diem trong vung goc phia truoc [-90, 90].
2. Bo diem co distance <= 0.
3. Lam tron goc theo bin, mac dinh 1 degree.
4. Gom distance theo angle bin.
5. Lay median distance cho moi bin.
6. Hien thi denoised LiDAR snapshot cho nguoi dung chon.

Metadata can luu:
- denoising_method = multi_scan_angle_binning_median.
- denoising_scans_count.
- angle_bin_deg.
- front_angle_min_deg/front_angle_max_deg.
- valid_points_count.

### 4. Select LiDAR Target
- Nguoi dung click 2 dau target tren LiDAR plot da denoise.
- UI danh dau P1/P2.
- Core lay cac diem nam giua hai goc.
- Loc jump distance bat thuong bang threshold mm.
- Hien so bar points.

### 5. Select Camera Target
- Nguoi dung click 2 dau target tren camera snapshot.
- UI danh dau P1/P2.
- Neu P1/P2 khong hop le, bao loi va cho chon lai.

### 6. Preview Mapping
- Noi suy diem LiDAR tren target sang duong noi hai pixel camera.
- Hien anh preview co mapped points.
- Hien sample summary: bar points, mapped points, angle range, avg distance.

### 7. Accept / Reject
- Accept: luu color, depth, depth_colormap, pair image va pair_*.json.
- Reject: bo snapshot, khong luu.
- Sau do quay lai stream realtime.

## Flow Compute UI
Compute UI khong can realtime phuc tap.
- Nut Load Dataset: dem pair_*.json va correspondence.
- Nut Run Calibration: goi compute_core de solve PnP/RANSAC.
- Left display hien log va reprojection preview.
- Right panel hien K, distCoeffs, R, T, inlier ratio, mean/median/max/std reprojection error.
- Sau khi co so lieu thuc nghiem moi dat PASS/WARNING/FAIL.

## Flow Fusion UI
Fusion UI hien validation realtime.
- RGB + LiDAR overlay.
- RealSense depth colormap.
- Sparse LiDAR depth.
- Metrics: projected_points, valid_depth_pairs, mean/median/max/std depth error.
- Nut Save Frame luu anh va metrics JSON.

## Threading trong PyQt
Can tach thread de UI khong bi treo:

Main UI Thread:
- Hien thi anh/plot.
- Nhan click/nut bam.
- Cap nhat status/log.

CameraWorker:
- Doc RealSense frame.
- Phat signal color/depth ve UI.

LiDARWorker:
- Doc iter_scans.
- Cap nhat latest_scan va scans_buffer.
- Phat signal plot data ve UI.

ComputeWorker:
- Chay PnP/RANSAC de tranh treo UI.
- Phat signal log/metrics ve UI.

FusionWorker:
- Doc frame + scan.
- Project va tinh metrics.
- Phat signal overlay/depth/sparse/metrics ve UI.

## Cac nut Collect de xuat
- Start Sensors.
- Stop Sensors.
- Capture Snapshot.
- Select LiDAR Points.
- Select Image Points.
- Reset Selection.
- Accept Sample.
- Reject Sample.
- Open Output Folder.

## Trang thai Collect de xuat
- IDLE.
- STREAMING.
- SNAPSHOT_CAPTURED.
- SELECTING_LIDAR.
- SELECTING_IMAGE.
- PREVIEW_READY.
- SAVED.
- REJECTED.
- ERROR.

## Viec can refactor truoc khi build UI
1. Tao src/core/lidar_core.py: normalize_angle, filter_scan, denoise_lidar_scans, polar_to_cartesian.
2. Tao src/core/camera_core.py: RealSense init, frame capture, depth scale.
3. Tao src/core/collect_core.py: map_lidar_to_image, build_calibration_data, save_sample.
4. Tao src/core/compute_core.py: load_data, solve_pnp, compute metrics, save result.
5. Tao src/core/fusion_core.py: load_calibration, project_lidar_points, process_scan, depth comparison.
6. Tao src/app_pyqt.py de lap UI.

## Nguyen tac thuc hien
- Khong pha 3 script CLI dang co.
- Moi core module tach ra phai duoc kiem tra bang py_compile.
- UI goi core, khong copy lai thuat toan.
- Moi buoc lon phai ghi log vao agent.
- Khong dat nguong PASS/WARNING/FAIL tuy tien khi chua co du lieu thuc nghiem.

## Ket luan
UI PyQt build duoc va phu hop voi yeu cau cua thay. Diem quan trong nhat la collect phai dung snapshot: stream de quan sat, capture de dong bang, chon diem tren snapshot, accept/reject roi quay lai stream. LiDAR snapshot phai tiep tuc dung denoise/binning median tu nhieu scan, khong dung scan don neu muon du lieu calibration on dinh.
