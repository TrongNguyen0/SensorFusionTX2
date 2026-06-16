# 12 - Fusion Jitter Stabilization

## Van de quan sat
Trong tab Fusion, cac diem LiDAR overlay bi rung/nhay va co cam giac hoi xoay thay vi dung im.

## Nguyen nhan co kha nang cao
1. Fusion UI truoc do dung truc tiep mot scan LiDAR tho cho moi frame. RPLidar co nhieu khoang cach va sai khac nho giua cac scan.
2. Camera va LiDAR khong dong bo thoi gian tuyet doi; moi vong lap lay frame camera va scan LiDAR gan nhat.
3. Dataset calibration hien tai co inlier ratio thap, nen projection co the nhay/le ch neu du lieu calibration chua that tot.
4. Neu cam bien hoac target rung/co lech co khi nho, overlay se thay doi ro hon.

## Sua doi da thuc hien
### app_pyqt.py
- Them FUSION_DENOISE_SCAN_COUNT = 5.
- FusionWorker khong con dua raw scan truc tiep vao process_scan.
- Moi scan duoc filter truoc bang filter_scan.
- Luu buffer nhieu scan gan nhat.
- Tao stable_scan bang denoise_scans voi median angle binning.
- process_scan dung stable_scan de project.
- Them metrics:
  - raw_scan_points.
  - filtered_scan_points.
  - fusion_denoise_scans.

### fusion_core.py
- Metrics text hien them raw/filtered/denoise scans.
- Doi label thanh Denoised LiDAR points de tranh hieu nham raw scan voi scan da loc.

## Co so khoa hoc
Trong collect, du lieu LiDAR da duoc lam on bang multi-scan angle binning median. Fusion validation cung nen dung cach on dinh tuong tu, vi muc tieu la kiem chung calibration tren canh gan nhu tinh, khong phai tracking vat the toc do cao.

Dung 5 scan la muc can bang:
- It hon 10 scan de giam do tre so voi collect.
- Nhieu hon 1 scan de giam rung do nhieu khoang cach/goc.
- Phu hop cho overlay validation trong phong.

## Trade-off
- Overlay on dinh hon.
- Co them do tre nho vi gom nhieu scan.
- Neu canh co vat the chuyen dong nhanh, smoothing co the lam diem cham hon thuc te. Trong do an calibration/fusion tinh, trade-off nay chap nhan duoc.

## Kiem chung
Da chay:
python -m py_compile src/app_pyqt.py src/core/fusion_core.py

Da chay import smoke test:
import app_pyqt; import core.fusion_core

Ket qua: pass.

## Can test thuc te
Chay app, vao tab Fusion va quan sat:
- Diem overlay co bot rung/xoay khong.
- Metrics hien Denoise scans tang den 5.
- Neu van rung manh, can xem lai calibration_result va bo du lieu calibration vi inlier ratio hien tai thap.
