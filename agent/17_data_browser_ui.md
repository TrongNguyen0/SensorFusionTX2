# 17 - Data Browser UI

## Yeu cau
Them phan Data trong UI: nguoi dung bam nut ben phai de xem anh da luu trong cac thu muc data, anh hien thi o vung ben trai.

## Da sua trong src/app_pyqt.py
1. Them mode moi: Data.
2. Them Data display:
   - ImageView lon de xem anh.
   - Label hien ten file va vi tri index.
3. Them Data controls ben phai:
   - Captured Color.
   - Captured Depth.
   - Depth Colormap.
   - Calibration Pair.
   - Fusion RGB.
   - Fusion Dense Depth.
   - Fusion Sparse Depth.
   - Fusion Overlay.
   - Previous.
   - Next.

## Thu muc ho tro
- data/captured_data/color
- data/captured_data/depth
- data/captured_data/depth_colormap
- data/captured_data/pair
- data/fusion_output/rgb
- data/fusion_output/depth_dense
- data/fusion_output/depth_sparse
- data/fusion_output/fusion

## Xu ly anh
- Doc anh bang imread_unicode de ho tro duong dan tieng Viet tren Windows.
- Anh depth grayscale/uint16 duoc chuyen sang colormap de hien thi duoc trong UI.
- Anh BGRA neu co duoc chuyen ve BGR.

## Cach dung
1. Chon mode Data.
2. Bam mot nut folder ben phai, vi du Calibration Pair.
3. Anh dau tien hien ben trai.
4. Bam Previous/Next de duyet.

## Kiem chung
Da chay:
python -m py_compile src/app_pyqt.py

Da chay import smoke test:
import app_pyqt

Ket qua: pass.

## Can test thuc te
Mo UI va thu bam tung nut folder. Can xac nhan anh hien dung va Previous/Next hoat dong voi duong dan co tieng Viet.
