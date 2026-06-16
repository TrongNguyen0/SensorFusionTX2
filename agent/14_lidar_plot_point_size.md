# 14 - LiDAR Plot Point Size

## Yeu cau
Giu denoise bin 1 degree, nhung giam kich thuoc diem tren LiDAR plot vi plot nhin qua day.

## Da sua
Trong src/app_pyqt.py, ham LidarPlotWidget._draw_points:
- Doi QPen width tu 4 xuong 2.

## Ly do
Khong doi ANGLE_BIN_DEG vi bin 1 degree giu du chi tiet cho collect calibration. Plot day chu yeu do 181 bin goc trong vung [-90, 90] va point size qua lon. Giam point size lam plot de nhin hon ma khong lam mat du lieu.

## Kiem chung
Da chay:
python -m py_compile src/app_pyqt.py

Ket qua: pass.
