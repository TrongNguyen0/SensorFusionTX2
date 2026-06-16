# 01 - Audit collect_calibration.py

## Muc tieu audit
Kiem tra buoc collect vi day la dau vao cua toan bo pipeline calibration va fusion. Neu du lieu collect sai, cac buoc compute va fusion phia sau se khong co gia tri khoa hoc.

## Vai tro cua collect_calibration.py
File nay dam nhiem:
- Khoi tao RPLidar qua COM3.
- Khoi tao Intel RealSense RGB-D.
- Doc scan LiDAR lien tuc bang thread nen.
- Loc diem LiDAR trong vung goc [-90, 90].
- Khu nhieu nhieu scan bang median theo goc lam tron.
- Cho nguoi dung chon hai dau target tren polar plot.
- Cho nguoi dung chon hai dau target tren anh RGB.
- Noi suy cac diem LiDAR tren target sang pixel anh.
- Luu anh color, depth, depth_colormap, anh pair va file pair_*.json.

## Phat hien chinh

### 1. Loi cleanup chac chan xay ra khi thoat
Ham cleanup duoc khai bao voi 4 tham so:
cleanup(lidar, csv_file, pipeline, lidar_thread)

Nhung cuoi file lai goi voi 3 tham so:
cleanup(lidar, csv_file, pipeline)

He qua: khi chuong trinh ket thuc, co the phat sinh TypeError va viec giai phong tai nguyen khong sach.

### 2. Neu RealSense loi thi LiDAR da mo nhung khong duoc dong
Thu tu hien tai:
1. init_lidar()
2. init_realsense()
3. init_csv()
4. vao try/finally

Neu init_realsense() loi RuntimeError: No device connected, chuong trinh chua vao khoi try/finally nen lidar.stop() va lidar.disconnect() khong duoc goi. Day la ly do COM co the bi ket sau khi camera loi.

### 3. Khong kiem tra RealSense truoc khi pipeline.start
init_realsense() goi truc tiep pipeline.start(config). Neu camera khong cam, bi app khac giu, sai USB hoac driver loi, thong bao loi khong than thien voi nguoi dung.

Can co buoc kiem tra rs.context().devices truoc khi start va in huong dan xu ly.

### 4. pipeline.stop co the loi neu pipeline chua start
Trong cleanup, pipeline.stop() duoc goi truc tiep. Neu pipeline khoi tao khong thanh cong hoac bien pipeline la None, cleanup co the loi tiep.

### 5. Thread LiDAR khong duoc truyen ra cleanup
main_loop tao thread cuc bo t = threading.Thread(...), nhung khong return t. cleanup co tham so lidar_thread nhung khong nhan duoc thread that.

Can quyet dinh mot trong hai cach:
- cleanup khong join thread, chi dat lidar_running = False va stop lidar.
- Hoac main_loop return thread / quan ly thread o main.

### 6. CSV bi ghi de moi lan chay
init_csv mo file lidar_data.csv bang mode w. Moi lan chay collect se xoa log cu. Neu can luu lich su thuc nghiem, nen chuyen sang append hoac tao file timestamp.

### 7. Metadata calibration con thieu
File pair_*.json hien co mapped_points va cartesian_points, nhung thieu cac thong tin quan trong de bao cao va tai lap thuc nghiem:
- lidar_port.
- color/depth resolution.
- timestamp dang ISO human-readable.
- raw selected lidar endpoints.
- selected image endpoints.
- denoise scan count va buffer point count.
- software/config version.
- camera serial neu lay duoc.

### 8. Khi map_lidar_to_image tra ve empty, calibrate van co the luu mau kem
map_lidar_to_image tra ve [] neu P1 khong nam ben trai P2. Tuy nhien calibrate khong kiem tra mapped co rong hay khong truoc khi show_result va save_all.

Can reject sample neu mapped_points rong.

### 9. UI collect moi o muc debug
UI hien tai co polar plot, window chon diem va result. Tuy nhien nguoi dung chua thay ro:
- Trang thai camera/LiDAR.
- So sample da luu.
- So diem target sau khi loc.
- Mau dang duoc accept hay reject.
- Huong dan phim dieu khien ro rang tren man hinh.

### 10. Gia dinh khoa hoc can ghi ro
Collect dang tao diem 3D LiDAR theo dang [x, 0, z]. Dieu nay gia dinh target nam tren mat phang quet cua LiDAR. Neu target lech khoi mat phang quet, du lieu correspondence se sai.

## Viec nen sua dau tien
Uu tien sua cac loi nen tang truoc khi nang UI:
1. Sua main/cleanup de thiet bi luon duoc dong sach khi RealSense loi.
2. Them preflight check cho RealSense.
3. Them kiem tra mapped_points rong thi khong luu mau.
4. Them metadata toi thieu vao pair_*.json.
5. Sau do moi nang UI hien thi trang thai va metrics.

## Tieu chi sau khi sua collect
- Neu RealSense khong ket noi, chuong trinh in thong bao ro va dong LiDAR sach.
- Thoat bang Ctrl+C khong gay TypeError.
- Mau calibration rong hoac chon sai khong bi luu.
- File JSON co metadata du de compute va bao cao.
- Nguoi dung nhin log/UI biet dang o buoc nao cua collect.
