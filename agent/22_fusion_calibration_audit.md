# 22 - Fusion Calibration Audit

## Van de nguoi dung bao

Sau khi thu du lieu calibration kha ky, fusion van sai:

- Diem LiDAR chi bam vao vat the o mot khoang cach nhat dinh.
- Khi vat the di xa/gan, diem project khong thay doi dung nhu mong doi.
- Diem bi lech trai/phai/tren/duoi kha nhieu.

## Kiem tra du lieu pair

Thu muc `data/captured_data/pair` hien co:

- 51 file JSON.
- 587 mapped correspondences.
- Khoang cach LiDAR trai dai tu khoang 0.55 m den hon 4.4 m.

Tuy nhien, cau truc correspondence co tinh suy bien:

- Moi sample la mot doan gan ngang tren anh.
- `pixel_y` hau het chi nam trong vung hep khoang 200-252 px.
- Cac diem trong cung sample khong phai cac click doc lap, ma duoc noi suy tu 2 diem anh bang `map_lidar_to_image()`.
- Dieu nay tao nhieu correspondence ve so luong, nhung thong tin hinh hoc doc lap thap.

## Kiem tra compute calibration

`calibration_metrics.json` hien tai:

- total correspondences: 587
- inlier count: 72
- inlier ratio: 12.27%
- all reprojection mean: 241.73 px
- inlier reprojection mean: 3.10 px

Ket luan:

- RANSAC tim duoc mot nghiem hop voi mot cum nho inlier.
- Phan lon du lieu bi xem la outlier.
- Inlier error nho khong du de khang dinh calibration tong the tot, vi inlier ratio qua thap.

## Kiem tra extrinsic hien tai

`calibration_result_pnp.npz` hien tai:

```text
T = [-7.86, -191.13, 3542.02] mm
Rzz = -0.9962
```

Dieu nay co nghia truc Z gan nhu bi lat. Voi diem LiDAR o truc giua `(x=0, y=0, z=distance)`,
Z camera xap xi:

```text
Z_camera ~= 3542 - 0.996 * Z_lidar
```

Bang mau:

```text
Z_lidar 0.5 m -> Z_camera 3.04 m
Z_lidar 0.9 m -> Z_camera 2.65 m
Z_lidar 1.8 m -> Z_camera 1.75 m
Z_lidar 3.0 m -> Z_camera 0.55 m
Z_lidar 3.5 m -> Z_camera 0.055 m
Z_lidar 4.0 m -> Z_camera -0.44 m
```

Ket luan:

- Diem LiDAR cang xa thi lai cang tien ve mat phang camera.
- Gan 3.5 m, diem gan nhu nam tai `Z_camera = 0`.
- Xa hon 3.5-4 m, diem co the bi coi la nam sau camera.
- Day la ly do fusion chi co ve dung o mot khoang cach nhat dinh va sai manh khi doi khoang cach.

## Kiem tra logic collect

`map_lidar_to_image()` hien tai:

- Nguoi dung click 2 diem dau/cuoi tren anh.
- Toan bo diem LiDAR trong khoang goc duoc noi suy tu 2 diem anh do.
- Neu diem dau/cuoi anh hoi lech, toan bo correspondence trong sample lech theo.
- Nhieu diem noi suy trong cung sample khong phai do doc lap.

Dieu nay de tao ra nhieu diem, nhung co nguy co lam PnP tuong nhu co nhieu correspondence hon thuc te.

## Kiem tra logic fusion UI

Fusion UI hien tai khac `fusion_calibration.py` cu:

- UI dung `filter_scan()`.
- UI dung `denoise_scans()` voi `FUSION_DENOISE_SCAN_COUNT = 5`.
- Sau do moi dua `stable_scan` vao `process_scan()`.

Code cu dua raw scan truc tiep vao `process_scan()`.

Khac biet nay co the anh huong do on dinh diem, nhung khong giai thich duoc loi lat truc Z. Loi goc hien tai van la extrinsic calibration.

## Ket luan

Nguyen nhan chinh cua fusion sai la calibration hien tai khong dang tin:

1. Extrinsic bi lat truc Z.
2. `Tz` rat lon, khoang 3.54 m.
3. Inlier ratio rat thap.
4. Du lieu correspondence co tinh suy bien do chu yeu la cac duong ngang va diem noi suy.
5. Fusion dung calibration nay nen diem LiDAR chi bam dung o mot vung khoang cach va lech khi vat the di xa/gan.

Trong buoc audit nay chua sua code.
