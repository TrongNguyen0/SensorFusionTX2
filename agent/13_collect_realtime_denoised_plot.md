# 13 - Collect Realtime Denoised Plot

## Van de
Trong Collect UI, plot realtime truoc do moi chi dung filter_scan:
- Bo distance <= 0.
- Giu goc [-90, 90].

Nhung chua denoise/binnning median. Trong khi khi Capture Snapshot lai denoise tu buffer. Dieu nay lam UI khong nhat quan: nguoi dung nhin mot dang du lieu luc streaming, nhung khi capture lai chon tren du lieu da loc nhieu hon.

## Da sua
### app_pyqt.py
1. LidarWorker gio duy tri scan_buffer rieng voi maxlen = DENOISE_SCAN_COUNT.
2. Moi scan tu RPLidar duoc xu ly theo pipeline:
   raw scan -> filter_scan -> scan_buffer -> denoise_scans -> emit ve UI.
3. Tin hieu scan_ready gio gui:
   - filtered_scan.
   - denoised_scan.
   - raw_scan_count.
4. Realtime LiDAR plot trong Collect hien denoised_scan thay vi filtered_scan.
5. Capture Snapshot khong denoise lai tu buffer rieng nua, ma copy dung latest_denoised_scan dang duoc hien thi.
6. Log khi capture hien:
   - raw points.
   - filtered points.
   - denoised points.
7. Header plot doi thanh: LiDAR Plot (denoised).

## Ly do thiet ke
Nguoi dung nen chon diem tren dung loai du lieu ma UI da hien thi. Neu realtime plot va snapshot dung hai pipeline khac nhau, target co the thay doi hinh dang/vi tri khi capture, gay kho thao tac va kho giai thich.

Dung denoised plot realtime giup:
- Giam rung/nhieu tren plot.
- Giu nhat quan giua streaming va snapshot.
- Tang do tin cay khi chon hai dau target.
- De giai thich trong bao cao: du lieu LiDAR collect duoc tien xu ly bang multi-scan median binning truoc khi nguoi dung gan correspondence.

## Trade-off
- Plot co the tre nhe vi gom nhieu scan.
- Doi lai, target on dinh hon va phu hop voi bai toan calibration tinh.

## Kiem chung
Da chay:
python -m py_compile src/app_pyqt.py

Da chay import smoke test:
import app_pyqt

Ket qua: pass.

## Can test thuc te
Chay UI va xac nhan:
- Plot realtime it rung hon.
- Header hien LiDAR Plot (denoised).
- Capture Snapshot khong lam plot thay doi dot ngot.
- Log capture hien raw/filter/denoised point counts.
