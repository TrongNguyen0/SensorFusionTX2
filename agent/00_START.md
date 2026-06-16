# Agent Worklog - SensorFusion

## 0. Ten de tai

Sensor Fusion giua LiDAR 2D va Camera RGB-D phuc vu bo sung do sau.

## 1. Muc tieu trung tam cua do an

Muc tieu cua do an khong chi la ve diem LiDAR len anh RGB, ma la xay dung mot pipeline calibration va fusion co the giai thich, do duoc sai so va kiem chung duoc ket qua.
He thong can tra loi duoc bon cau hoi:

- Thu du lieu calibration da dung chua?
- Ket qua calibration co chinh xac khong?
- Fusion sau calibration co khop voi anh va depth khong?
- Du lieu LiDAR co the phuc vu bo sung/kiem chung do sau o muc nao?

Trong pham vi do an, he thong duoc xac dinh la prototype khoa hoc: co quy trinh, co chi so danh gia, co anh minh hoa, co UI/log ho tro nguoi dung. Khong tuyen bo la he thong depth completion hoan chinh cap san pham.

## 2. Pham vi kha thi trong 2 ngay

Trong 2 ngay, muc tieu kha thi la tao mot pipeline hoan chinh o muc do do an:

1. Collect du lieu calibration co huong dan va luu du lieu ro rang.
2. Compute calibration bang PnP/RANSAC.
3. Danh gia calibration bang reprojection error va inlier ratio.
4. Fusion realtime de chieu diem LiDAR len anh RGB.
5. Tao sparse LiDAR depth map sau khi project.
6. So sanh depth LiDAR voi depth RealSense tai cac pixel hop le.
7. Luu anh, metrics va cap nhat README/bao cao theo so lieu that.

Nhung viec khong nen lam trong 2 ngay:

- Tu dong detect target hoan toan.
- Depth completion bang deep learning.
- UI desktop phuc tap.
- So sanh nhieu thuat toan nang cao.
- Toi uu hieu nang sau.

## 3. Pipeline tong the

Pipeline chuan cua do an gom bon giai doan:

1. Thu thap du lieu calibration

   - Input: scan LiDAR, anh RGB, anh depth, target calibration.
   - Xu ly: loc goc, khu nhieu scan, chon target tren LiDAR va anh RGB, noi suy cap diem.
   - Output: anh va file pair_*.json chua mapped_points.
2. Tinh calibration

   - Input: pair_*.json va camera intrinsics tu RealSense.
   - Xu ly: doi polar sang Cartesian, tao cap 3D-2D, solvePnPRansac.
   - Output: K, distCoeffs, R, T, inliers, reprojection metrics.
3. Kiem tra va danh gia calibration

   - Input: K, R, T, distCoeffs va tap correspondence.
   - Xu ly: project lai diem 3D len anh va so sanh voi pixel goc.
   - Output: mean/median/max/std reprojection error, inlier ratio, anh kiem chung.
4. Fusion va validation

   - Input: frame RGB/depth realtime, scan LiDAR, calibration_result.
   - Xu ly: project diem LiDAR len RGB, tao sparse depth LiDAR, so sanh voi RealSense depth.
   - Output: RGB overlay, sparse depth map, depth error metrics, anh/file ket qua.

## 4. Ket qua mong muon

Ket qua cuoi cung cua he thong can co:

- File calibration_result_pnp.npz chua K, distCoeffs, R, T.
- File metrics calibration dang JSON/TXT.
- So luong correspondence va so luong inlier.
- Mean, median, max, std reprojection error.
- Anh minh hoa reprojection/overlay.
- Anh RGB + LiDAR overlay khi fusion.
- Sparse depth map tao tu LiDAR sau khi project len anh.
- So sanh depth LiDAR voi depth RealSense tai pixel hop le.
- README moi mo ta dung pipeline hien tai.
- Bao cao co so lieu thuc nghiem, khong ghi ket luan dinh luong neu chua co du lieu.

## 5. Lam sao biet calibration dung hay sai

Calibration khong duoc danh gia bang cam giac duy nhat. Can ket hop ba nhom bang chung:

### 5.1. Reprojection error

Sau khi co R va T, moi diem LiDAR 3D duoc project len anh. Sai so la khoang cach giua pixel project va pixel ground truth/noi suy trong du lieu calibration.

Cong thuc:
e = sqrt((u_projected - u_groundtruth)^2 + (v_projected - v_groundtruth)^2)

Can bao cao:

- Mean reprojection error.
- Median reprojection error.
- Max reprojection error.
- Standard deviation.
- Inlier / total correspondence.

### 5.2. Kiem chung truc quan

Neu calibration dung, diem LiDAR sau khi chieu len anh RGB phai bam vao dung vat the/target trong nhieu vi tri khac nhau.
Neu diem bi lech co he thong sang trai/phai/tren/duoi, hoac chi dung o mot vung nho nhung sai o vung khac, calibration co van de.

### 5.3. So sanh depth LiDAR va depth RealSense

Voi moi diem LiDAR project vao pixel hop le (u, v):

- Depth LiDAR lay tu toa do sau khi transform sang camera, thuong la Zc.
- Depth RealSense lay tu depth_img[v, u].
- Sai so depth: abs(depth_lidar - depth_realsense).

Can bao cao:

- So diem co ca LiDAR depth va RealSense depth hop le.
- Mean depth error.
- Median depth error.
- Max depth error.

## 6. Do chinh xac cua thuat toan phu thuoc vao dau

Do chinh xac cua pipeline phu thuoc vao:

- Chat luong du lieu calibration.
- Sai so khi chon hai dau target tren LiDAR va anh RGB.
- So luong va do phan bo mau calibration.
- Nhieu do khoang cach cua LiDAR.
- Do chinh xac intrinsics va depth cua RealSense.
- Do cung va do on dinh cua gia lap LiDAR-camera.
- Gia dinh LiDAR 2D nam tren mat phang y = 0.
- Nguong RANSAC va chat luong tap correspondence 3D-2D.

Can ghi ro trong bao cao: thuat toan PnP/RANSAC khong tu tao ra ket qua tot neu tap correspondence ban dau sai. Chat luong calibration phu thuoc truc tiep vao chat luong du lieu thu thap.

## 7. UI nguoi dung

UI can bao phu tu collect den compute va fusion. Doi tuong nguoi dung la sinh vien/ky thuat vien/nguoi van hanh can thu du lieu, chay calibration va kiem chung sensor fusion.

### 7.1. Collect UI

Muc tieu: giup nguoi dung thu du lieu dung quy trinh.
Can hien thi:

- Trang thai LiDAR va camera.
- Anh RGB realtime.
- Bieu do LiDAR polar hoac top-view.
- So diem LiDAR hop le.
- So mau calibration da luu.
- Huong dan chon target.
- Anh ket qua sau khi noi suy diem tren target.
- Trang thai accept/reject sample.

### 7.2. Compute/Calibration UI hoac log

Muc tieu: cho nguoi dung biet calibration co dat hay khong.
Can hien thi/in ra:

- So file pair_*.json duoc nap.
- Tong so correspondence.
- So inlier/outlier.
- Mean/median/max/std reprojection error.
- K, R, T, distCoeffs.
- Trang thai PASS/WARNING/FAIL theo nguong thuc nghiem.
- Anh kiem chung reprojection.

### 7.3. Fusion/Validation UI

Muc tieu: kiem chung calibration trong thoi gian thuc.
Can hien thi:

- RGB + LiDAR overlay.
- RealSense depth colormap.
- Sparse LiDAR depth map.
- Metrics ve so diem project thanh cong.
- So diem co depth RealSense hop le.
- Mean/median depth error neu tinh duoc.
- Phim luu ket qua va thoat chuong trinh.

Trong 2 ngay, UI nen lam bang OpenCV window + text overlay + phim dieu khien. Khong can lam app GUI lon.

## 8. Tieu chi dat/chua dat

Do chua co so lieu thuc nghiem cuoi cung, khong dat nguong tuy tien. Sau khi chay du lieu that, co the xac dinh nguong PASS/WARNING/FAIL dua tren ket qua.

Tam thoi, he thong duoc xem la dat ve mat do an neu:

- Thu duoc tap calibration co nhieu mau va nhieu vi tri target.
- Compute chay thanh cong va co inlier ro rang.
- Reprojection error duoc tinh va luu.
- Diem LiDAR overlay khop tuong doi voi vat the tren anh RGB.
- Sparse LiDAR depth tao duoc trong frame anh.
- So sanh duoc depth LiDAR voi depth RealSense tai cac pixel hop le.
- Toan bo ket qua co the luu lai de dua vao bao cao.

## 9. Thu tu uu tien code

1. Audit collect_calibration.py.
2. Sua khoi tao thiet bi va cleanup de tranh loi RealSense/LiDAR lam treo chuong trinh.
3. Chuan hoa cau hinh: port, resolution, output path.
4. Nang compute_calibration.py: luu distCoeffs, metrics, inliers, anh kiem chung.
5. Nang fusion_calibration.py: cv2.projectPoints, RGB overlay, sparse depth, depth comparison.
6. Viet/cap nhat README theo pipeline moi.
7. Cap nhat bao cao bang so lieu that.

## 10. Nguyen tac lam viec cua agent

Moi thay doi can ghi ro:

- Dang kiem tra gi.
- Phat hien van de gi.
- Se sua file nao.
- Da sua nhung gi.
- Da kiem chung bang lenh nao.
- Ket qua kiem chung ra sao.
- Con rui ro hoac cau hoi nao can nguoi dung xac nhan.

Khong tu y bia so lieu, thong so ky thuat hoac ket qua thuc nghiem. Neu chua co du lieu that, ghi ro la can do/kiem chung them.

## 11. Cau hoi can xac nhan khi den giai doan thuc nghiem

- Target calibration cu the la vat gi, kich thuoc bao nhieu?
- LiDAR va camera duoc lap co dinh theo cau hinh nao?
- RealSense depth scale tren may dang la bao nhieu?
- Can dung nguong nao de xem reprojection error la dat?
- Ket qua cuoi cung uu tien demo truc quan hay so lieu dinh luong?
