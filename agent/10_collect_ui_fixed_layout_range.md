# 10 - Collect UI Fixed Layout and LiDAR Range

## Yeu cau
Sua Collect UI:
- Camera view va LiDAR plot phai duoc chia doi co dinh trong vung hien thi.
- LiDAR plot khong duoc tu dong nhay thang do theo scan.
- Cac vach khoang cach tren plot phai co dinh.
- Can giai thich co so chon muc gioi han hien thi LiDAR.

## Da sua trong src/app_pyqt.py
1. Them constant:
   - LIDAR_DISPLAY_RANGE_MM = 6000.
   - LIDAR_GRID_STEP_MM = 1000.

2. Collect display layout:
   - Camera view nam hang tren.
   - LiDAR plot nam hang duoi.
   - setRowStretch(0, 1) va setRowStretch(1, 1) de hai vung chia doi on dinh.

3. LiDAR plot:
   - Bo auto-scale theo max distance cua scan hien tai.
   - Dung display_range co dinh 6000 mm.
   - Vach luoi co dinh moi 1000 mm.
   - Hien label 1m, 2m, ..., 6m.
   - Header hien fixed range thay vi range thay doi theo scan.

## Co so chon gioi han 6000 mm
Muc 6000 mm khong phai chon tuy tien. No dua tren cac co so sau:

1. Ke thua logic UI collect ban dau
Trong collect_calibration.py cu, polar plot da dung ax.set_ylim(0, 6000). Do do 6000 mm la gioi han hien thi da duoc dung trong pipeline truoc khi co PyQt. UI moi giu lai muc nay de khong thay doi hanh vi quan sat.

2. Phu hop voi bai toan calibration trong phong
Calibration LiDAR-camera voi target thu cong thuong duoc thuc hien trong khoang gan den trung binh. Vung 0-6m du bao phu target trong phong, dong thoi khong lam target gan bi nen qua nho tren plot.

3. On dinh thao tac nguoi dung
Neu plot tu auto-scale theo tung scan, cung mot target co the nhay vi tri hien thi khi co diem xa/gan xuat hien hoac bien mat. Dieu nay lam nguoi dung kho chon hai dau target va kho so sanh giua cac snapshot. Co dinh range giup moi snapshot co cung he tham chieu.

4. Phu hop voi bao cao khoa hoc
Mot thang do co dinh giup ket qua visualization tai lap hon: cac anh chup UI/plot co cung ti le, de so sanh giua cac lan thu du lieu va de trinh bay trong bao cao.

## Co so chon vach 1000 mm
Vach 1m la muc chia de doc truc quan trong moi truong trong phong: du chi tiet de uoc luong khoang cach target, nhung khong qua day lam roi plot.

## Kiem chung
Da chay:
python -m py_compile src/app_pyqt.py

Ket qua: pass.

## Chua kiem chung
Chua mo UI truc tiep de xem bo cuc tren man hinh that. Can chay:
python src/app_pyqt.py

Can xac nhan bang mat:
- Camera va LiDAR plot co chia doi dung khong.
- Plot khong con nhay thang do khi scan thay doi.
- Vach 1m den 6m hien on dinh.
