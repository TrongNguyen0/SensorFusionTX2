# 02 - Collect Fix Log

## Muc tieu
Sua cac loi nen tang cua collect_calibration.py truoc khi nang UI va metadata.

## Da sua trong src/collect_calibration.py
1. Them preflight check cho RealSense bang rs.context().query_devices().
2. In ten va serial RealSense neu doc duoc.
3. Neu khong co RealSense, bao loi ro rang thay vi chi RuntimeError mo ho.
4. Cho cleanup nhan tham so mac dinh None de an toan khi khoi tao loi giua chung.
5. Dong csv_file, lidar va pipeline trong try/except rieng de tranh loi domino khi cleanup.
6. Sua main de init tai nguyen nam trong try/finally, dam bao LiDAR duoc dong neu RealSense loi.
7. Kiem tra mapped_points rong sau map_lidar_to_image; neu rong thi reject sample va khong luu pair_*.json.

## Kiem chung da chay
Lenh: python -m py_compile src/collect_calibration.py
Ket qua: pass, khong co loi cu phap.

## Chua kiem chung duoc
Chua chay hardware test voi RealSense/LiDAR vi can thiet bi ket noi truc tiep.

## Rui ro con lai
- Thread LiDAR van duoc tao trong main_loop va khong join that su trong cleanup vi main_loop khong return thread. Hien tai daemon thread va lidar_running=False giam rui ro, nhung nen don dep tiep.
- CSV van ghi de moi lan chay. Can doi sang timestamp hoac append o buoc sau.
- Metadata trong pair_*.json con thieu. Can bo sung o buoc sau.
- UI collect chua co overlay huong dan/trang thai day du.
