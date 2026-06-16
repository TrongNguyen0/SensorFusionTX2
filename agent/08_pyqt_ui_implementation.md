# 08 - PyQt UI Implementation

## Muc tieu
Bat dau build UI PyQt theo ke hoach 07, uu tien Collect UI chi tiet: stream camera, plot LiDAR, capture snapshot, click chon diem, preview, accept/reject.

## Dependency
Da cai PyQt5 thanh cong bang pip:
python -m pip install PyQt5

Them file requirements-ui.txt voi noi dung:
PyQt5>=5.15

Khong cai pyqtgraph. LiDAR plot hien duoc ve bang QPainter de giam phu thuoc.

## File moi da tao
- src/core/__init__.py
- src/core/lidar_core.py
- src/core/collect_core.py
- src/app_pyqt.py
- requirements-ui.txt

## Logic da boc tach
### lidar_core.py
Giu lai logic tu collect cu:
- normalize_angle.
- polar_to_cartesian.
- filter_scan trong vung [-90, 90].
- denoise_scans bang multi-scan angle binning median.
- extract_bar_points theo hai dau target va loc jump distance.
- nearest_lidar_point de click tren plot chon diem gan nhat.

### collect_core.py
Giu lai logic mapping/lui du lieu:
- map_lidar_to_image.
- build_calibration_data co metadata.
- render_pair_preview.
- save_sample luu color/depth/depth_colormap/pair image/pair json.

## UI app_pyqt.py hien tai
### Bo cuc
- Ben trai: display stack.
- Ben phai: control panel, mode combo, nut bam, huong dan, log.
- Mode hien co: Collect / Compute / Fusion.

### Collect UI da co
- Start Sensors.
- Stop Sensors.
- Capture Snapshot.
- Reset Selection.
- Accept Sample.
- Reject Sample.
- Camera stream hien tren ImageView.
- LiDAR plot ve bang QPainter.
- Capture snapshot dong bang color/depth va denoise buffer LiDAR.
- Click 2 diem tren LiDAR plot.
- Click 2 diem tren anh camera.
- Preview mapped points.
- Accept luu sample, Reject bo sample.
- Sau accept/reject quay lai stream.

### Compute/Fusion UI tam thoi
- Co nut Run Calibration de goi compute_calibration.py bang QProcess.
- Co nut Launch Fusion Validation de goi fusion_calibration.py bang QProcess.
- Output script duoc dua vao log.
- Phan nay la tam thoi; sau nay co the nhung sau hon vao UI.

## Kiem chung da chay
1. Cai PyQt5: thanh cong.
2. Syntax check:
   python -m py_compile src/app_pyqt.py src/core/lidar_core.py src/core/collect_core.py
   Ket qua: pass.
3. PyQt import check:
   python -c "import PyQt5"
   Ket qua: pass.
4. app_pyqt import smoke test:
   import app_pyqt
   Ket qua: pass.

## Chua kiem chung
Chua mo UI that trong GUI va chua test voi RealSense/RPLidar. Can chay:
python src/app_pyqt.py

Khi test hardware can xac nhan:
- Start Sensors co mo camera va LiDAR khong.
- Camera stream co cap nhat dung khong.
- LiDAR plot co hien scan dung khong.
- Capture Snapshot co dong bang dung frame/scan khong.
- Click tren plot chon dung diem gan nhat khong.
- Click tren anh co dung toa do pixel khong.
- Accept co luu pair_*.json dung schema khong.
- Reject co quay lai streaming khong.

## Nguyen tac tiep theo
Khong pha 3 script CLI hien tai. UI dang goi core va co the goi script cu bang QProcess. Neu UI gap loi hardware, collect_calibration.py/compute_calibration.py/fusion_calibration.py van la duong lui.
