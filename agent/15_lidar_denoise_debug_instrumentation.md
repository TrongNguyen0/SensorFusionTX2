# 15 - LiDAR Denoise Debug Instrumentation

## Muc tieu
Chua sua thuat toan denoise. Them debug de kiem chung gia thuyet: cac diem tren plot Collect co phai la ghost/trailing tu scan cu trong buffer hay khong.

## Gia thuyet can kiem tra
Khi vat the di chuyen, mot so angle bin chi xuat hien trong scan cu nhung van con trong buffer. denoise_scans lay hop cac bin trong nhieu scan, nen cac bin cu co the van duoc ve va tao vet keo.

## Da them trong core/lidar_core.py
### analyze_denoise_bins(scans, denoised_points)
Ham nay tinh:
- current_bins: so angle bin co mat trong scan moi nhat.
- stale_bins: so diem denoised khong co mat trong scan moi nhat.
- max_bin_age: tuoi lon nhat cua bin, age=0 la scan moi nhat.
- point_ages: tuoi cua tung diem denoised.

## Da them trong app_pyqt.py
1. LidarWorker emit them debug metrics.
2. LidarPlotWidget hien header:
   - points.
   - current bins.
   - stale bins.
   - max age.
3. Plot to mau theo age:
   - Xanh la: age 0, bin co trong scan moi nhat.
   - Vang: age 1-2, bin tu scan gan day.
   - Cam/do: age > 2, bin cu hon.
4. Khi capture snapshot, log them stale bins va max age.

## Cach doc ket qua khi test
Neu khi di chuyen vat the:
- stale bins tang cao.
- cac diem keo vet co mau vang/cam/do.
=> Gia thuyet ghost tu buffer la dung. Luc do moi nen sua denoise theo current-frame gated denoise.

Neu stale bins gan 0 nhung van co cum diem/la vet:
=> Nguyen nhan khong phai buffer ghost. Can xem lai plot transform, scale, hoac du lieu LiDAR thuc te.

Neu denoised points vuot qua khoang 181 voi bin 1 degree trong [-90, 90]:
=> Co loi binning hoac angle bin khong nhu ky vong.

## Kiem chung
Da chay:
python -m py_compile src/app_pyqt.py src/core/lidar_core.py

Da chay import smoke test:
import app_pyqt; from core.lidar_core import analyze_denoise_bins

Ket qua: pass.

## Buoc tiep theo
Chay UI, di chuyen vat the va chup/ghi lai:
- points.
- current bins.
- stale bins.
- max age.
- mau cua cum diem dang nghi ngo.

Sau do quyet dinh co can sua denoise theo current-frame gated denoise hay khong.
