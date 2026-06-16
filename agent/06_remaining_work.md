# 06 - Remaining Work Against 00_START

## Trang thai tong quan
Da xong xong song code cho ba buoc collect, compute va fusion. Tuy nhien yeu cau trong 00_START khong chi la code. Con can kiem chung thuc nghiem, sinh ket qua, viet README va cap nhat bao cao bang so lieu that.

## Da hoan thanh ve code
- Collect co preflight RealSense, cleanup an toan, metadata JSON va accept/reject sample.
- Compute co PnP/RANSAC, distCoeffs, inliers, reprojection metrics, metrics JSON va preview images.
- Fusion co cv2.projectPoints, RGB overlay, sparse LiDAR depth, depth comparison va metrics JSON.
- Agent logs da ghi day du qua cac buoc 01 den 05.

## Chua hoan thanh trong 00_START

### 1. Thu du lieu calibration co nhieu mau va nhieu vi tri target
Trang thai: chua xac nhan sau khi sua code.
Can lam: chay collect voi hardware that va thu bo sample sach.
Ket qua can co: pair_*.json moi, anh color/depth/pair moi, sample metadata moi.

### 2. Compute calibration bang du lieu moi
Trang thai: code da san sang, chua chay main sau khi sua.
Can lam: chay python src/compute_calibration.py khi RealSense ket noi.
Ket qua can co: calibration_result_pnp.npz moi co distCoeffs/rvec/tvec/inliers/errors.

### 3. Danh gia calibration bang so lieu that
Trang thai: code co tinh metrics, chua co metrics moi sau thuc nghiem.
Can lam: doc data/calibration_result/calibration_metrics.json sau khi compute.
Ket qua can co: total correspondence, inlier ratio, mean/median/max/std reprojection error.

### 4. Anh kiem chung reprojection
Trang thai: code co tao preview, chua co preview sau khi chay compute moi.
Can lam: mo data/calibration_result/reprojection_preview va chon anh dua vao bao cao.

### 5. Fusion validation voi hardware that
Trang thai: code da san sang, chua chay thuc te sau khi sua.
Can lam: chay python src/fusion_calibration.py.
Ket qua can co: overlay, sparse depth, depth comparison metrics.

### 6. So sanh depth LiDAR voi RealSense bang so lieu that
Trang thai: code co tinh, chua co ket qua that.
Can lam: luu vai frame bang phim S trong fusion.
Ket qua can co: data/fusion_output/metrics/*.json voi valid_depth_pairs va depth_error_mm.

### 7. PASS/WARNING/FAIL
Trang thai: chua co nguong vi chua co so lieu thuc nghiem on dinh.
Can lam: sau khi co metrics, dat nguong hop ly cho do an.
Ghi chu: khong duoc bia nguong truoc khi xem du lieu that.

### 8. README moi
Trang thai: chua lam.
Can lam: viet README theo pipeline moi, thay README cu dang lech Homography/PnP.
Noi dung can co: hardware, software, collect, compute, fusion, outputs, metrics, troubleshooting.

### 9. Bao cao Word
Trang thai: moi co ban chuong 1-3 va khung muc luc.
Can lam: cap nhat cac chuong thuc nghiem bang so lieu that.
Noi dung can bo sung: quy trinh thu du lieu, mo hinh toan, thuat toan, ket qua, danh gia sai so, fusion validation.

### 10. Cau hoi thuc nghiem can xac nhan
- Target calibration cu the la vat gi va kich thuoc bao nhieu?
- Lidar-camera duoc lap co dinh nhu the nao?
- Co can xoa/luu rieng bo pair cu truoc khi thu lai khong?
- Muon dung bao nhieu mau calibration cho ban cuoi?
- Muc uu tien cuoi cung: demo truc quan hay bang so lieu?

## Viec nen lam tiep theo
Truoc khi viet README/bao cao, nen tao mot script hoac lenh tong hop ket qua sau khi chay compute/fusion. Nhung viec thuc te ngay tiep theo nen la:
1. Chay hardware test collect.
2. Thu sample calibration sach.
3. Chay compute va doc metrics.
4. Chay fusion validation va luu frame.
5. Sau do moi viet README va bao cao bang ket qua that.
