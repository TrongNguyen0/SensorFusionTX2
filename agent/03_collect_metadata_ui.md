# 03 - Collect Metadata and Sample Review

## Muc tieu
Nang buoc collect tu muc chay duoc sang muc tao du lieu calibration co the kiem tra, tai lap va dua vao bao cao.

## Da sua trong src/collect_calibration.py
1. Dua cac thong so cau hinh thanh constant:
   - COLOR_WIDTH, COLOR_HEIGHT.
   - DEPTH_WIDTH, DEPTH_HEIGHT.
   - CAMERA_FPS.
   - FRONT_ANGLE_MIN, FRONT_ANGLE_MAX.
   - DENOISE_SCAN_COUNT.
   - BAR_DISTANCE_JUMP_THRESHOLD_MM.

2. Dung cac constant nay trong:
   - filter_scan.
   - init_realsense.
   - denoise_lidar_scans.
   - loc diem target tren thanh.

3. Bo sung review UI truoc khi luu sample:
   - Window Result hien so mapped points va so sample da luu.
   - Enter hoac A: chap nhan va luu sample.
   - R: loai sample, khong luu JSON/anh.

4. Bo sung sample summary trong terminal:
   - So bar points.
   - So mapped points.
   - Khoang goc cua target.
   - Khoang cach trung binh.

5. Bo sung metadata vao pair_*.json:
   - timestamp_iso.
   - source_script.
   - hardware: lidar model, lidar port, camera model.
   - capture_config: resolution, FPS, front angle range.
   - mapped_points_count.
   - denoising_scans_count.
   - bar_distance_jump_threshold_mm.

## Kiem chung da chay
Lenh: python -m py_compile src/collect_calibration.py
Ket qua: pass, khong co loi cu phap.

## Chua kiem chung duoc
Chua test UI voi hardware thuc te. Can chay collect voi LiDAR va RealSense de xac nhan:
- Window Result hien dung text overlay.
- Enter/A luu sample.
- R reject sample.
- File pair_*.json co metadata moi.

## Gia tri khoa hoc tang them
Du lieu collect bay gio co them metadata va co buoc chap nhan/loai mau. Dieu nay giup giam nguy co dua sample kem chat luong vao compute_calibration.py va giup bao cao co thong tin tai lap thuc nghiem.

## Buoc tiep theo de xuat
Chuyen sang compute_calibration.py:
- Luu distCoeffs vao calibration_result_pnp.npz.
- Luu metrics ra JSON/TXT.
- Luu inliers.
- Tao anh/du lieu kiem chung reprojection.
