# 09 - Compute Unicode and Preview Fix

## Loi gap trong UI Compute
Khi chay compute tu PyQt UI, script da tinh duoc calibration va metrics nhung crash o cuoi khi print duong dan co ky tu tieng Viet. Loi cu the:
UnicodeEncodeError: cp1252 cannot encode Vietnamese path characters.

Dong thoi OpenCV canh bao khong doc duoc pair_*.png de tao reprojection preview. Nguyen nhan co the la:
- pair image khong ton tai voi bo data hien tai, hoac
- cv2.imread tren Windows gap van de voi duong dan Unicode.

## Da sua
### compute_calibration.py
1. Reconfigure stdout/stderr sang UTF-8 voi errors=replace.
2. Them imread_unicode bang np.fromfile + cv2.imdecode.
3. Them imwrite_unicode bang cv2.imencode + tofile.
4. Them fallback source image: thu pair_*.png truoc, neu khong duoc thi dung color_*.png.
5. save_preview_images dung Unicode-safe IO va in so anh bi skip neu co.

### app_pyqt.py
1. Khi chay script bang QProcess, set PYTHONIOENCODING=utf-8.
2. Giam nguy co crash khi script in duong dan Unicode trong UI log.

## Kiem chung da chay
1. Syntax/import: pass.
2. Chay lai compute_calibration.py that voi RealSense ket noi: pass.

## Ket qua compute sau khi sua
- Loaded 19 pair files.
- Loaded 304 valid correspondences.
- Inliers: 30/304.
- Mean reprojection error inliers: 5.93 px.
- Median: 5.91 px.
- Max: 12.29 px.
- Std: 3.56 px.
- Saved 8 reprojection preview images.
- Saved calibration_result_pnp.npz.
- Saved data/calibration_result/calibration_metrics.json.

## Nhan xet can than
Mean error tren inliers tam on, nhung inlier ratio thap: 30/304. Chua nen ket luan calibration tot. Can xem preview images va co the thu lai sample calibration sach hon.

## Buoc tiep theo
1. Mo data/calibration_result/reprojection_preview de xem diem project co khop khong.
2. Neu preview sai nhieu, thu lai dataset calibration bang UI collect moi.
3. Sau khi co dataset sach, chay compute lai va so sanh inlier ratio/reprojection error.
