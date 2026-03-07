# LiDAR-Camera Calibration System

## 📋 Giới thiệu

Hệ thống calibration để đồng bộ **RPLidar A1M8 (2D LiDAR)** với **Intel RealSense D435 (RGB-D Camera)**.

### Mục tiêu
Tìm ma trận biến đổi (R, T) để chiếu điểm 3D từ LiDAR lên tọa độ 2D của camera:

```
P_camera = R × P_lidar + T
[u, v] = K × P_camera / Z
```

## 🔧 Yêu cầu

### Phần cứng
- Intel RealSense D435
- RPLidar A1M8
- Khay gắn cố định LiDAR phía trên Camera
- Thanh target (vạch trắng/đen)

### Phần mềm
```bash
pip install pyrealsense2 numpy opencv-python rplidar-roboticia scipy
```

## 📁 Cấu trúc file

```
sensorfusion/
├── collect_data_v2.py    # Thu thập dữ liệu calibration
├── compute_v2.py         # Tính ma trận R, T
├── fusion_v2.py          # Hiển thị kết quả real-time
├── calibration_data.pkl  # Dữ liệu thu thập (tự sinh)
├── matrix.npy            # Ma trận calibration (tự sinh)
└── README.md
```

## 🚀 Hướng dẫn sử dụng

### Bước 1: Thu thập dữ liệu

```bash
python collect_data_v2.py
```

**Quy trình:**
1. Đặt thanh target (trắng/đen) phía trước camera + LiDAR (~0.5m)
2. **Kéo chuột trái** để vẽ vùng bao quanh thanh target
3. Di chuyển thanh **lên/xuống** để LiDAR quét nhiều điểm
4. Nhấn **SPACE** khi đường đỏ (fitted line) khớp với thanh target
5. Di chuyển target **ra xa hơn** (1m, 1.5m, 2m...) và lặp lại
6. Thu thập **ít nhất 20-30 mẫu** ở các khoảng cách khác nhau
7. Nhấn **S** để lưu và thoát

**Tips:**
- Thanh target phải dài và có contrast cao
- Di chuyển chậm để LiDAR kịp quét
- Đảm bảo có mẫu ở ít nhất 3-4 khoảng cách khác nhau

### Bước 2: Tính toán Calibration

```bash
python compute_v2.py
```

Script sẽ:
1. Load dữ liệu từ `calibration_data.pkl`
2. Chạy tối ưu hóa với nhiều initial guess
3. Hiển thị kết quả và reprojection error
4. Lưu ma trận vào `matrix.npy`

**Kết quả tốt:** Average error < 10 pixels

### Bước 3: Test kết quả

```bash
python fusion_v2.py
```

Các điểm LiDAR sẽ được overlay lên ảnh camera với màu theo khoảng cách:
- 🟢 Xanh lá = Gần
- 🟡 Vàng = Trung bình  
- 🔴 Đỏ = Xa

**Phím tắt:**
- `D`: Toggle depth overlay
- `S`: Screenshot
- `Q`: Thoát

## 📐 Lý thuyết

### RPLidar A1M8
- **Góc quét: 360°** (quay liên tục)
- **LiDAR 2D**: Chỉ quét trong mặt phẳng ngang (không có chiều cao Z)
- **Lắp ngược 180°**: Mặt trước LiDAR quay ngược với camera
  - Góc 0° của LiDAR = hướng ngược camera
  - Góc 180° của LiDAR = hướng camera nhìn

### Hệ tọa độ

**LiDAR (2D):**
- X: Hướng phía trước (depth)
- Y: Hướng ngang (left/right)
- Z: Luôn = 0 (2D LiDAR, không có chiều cao)

**Camera:**
- X: Phải
- Y: Xuống
- Z: Phía trước (depth)

### Ma trận biến đổi

```
[X_cam]   [r11 r12 r13]   [X_lidar]   [tx]
[Y_cam] = [r21 r22 r23] × [Y_lidar] + [ty]
[Z_cam]   [r31 r32 r33]   [   0   ]   [tz]
```

Với LiDAR 2D (Z=0), ma trận rút gọn:
```
X_cam = r11*X_lidar + r12*Y_lidar + tx
Y_cam = r21*X_lidar + r22*Y_lidar + ty
Z_cam = r31*X_lidar + r32*Y_lidar + tz
```

### Projection

```
u = fx * X_cam/Z_cam + cx
v = fy * Y_cam/Z_cam + cy
```

## ⚠️ Troubleshooting

### LiDAR không kết nối
- Kiểm tra cổng COM trong Device Manager
- Thay đổi `LIDAR_PORT` trong code

### Reprojection error cao
- Thu thập thêm dữ liệu
- Đảm bảo target được detect chính xác
- Kiểm tra LiDAR có gắn chắc không

### Điểm project sai vị trí
- LiDAR có thể xoay 180 độ → compute_v2.py tự xử lý
- Kiểm tra `LIDAR_CENTER_ANGLE` có đúng không

## 📊 Kết quả mẫu

```
[ROTATION]
Euler Angles: [0.5°, 179.8°, -0.2°]  → LiDAR xoay ngược 180°

[TRANSLATION]
T = [0.002, -0.041, 0.005] meters
  - ty = -41mm: LiDAR trên camera 41mm ✓

[REPROJECTION ERROR]
Average error: 4.2 ± 1.8 pixels ✓ Excellent!
```

## 📚 Tham khảo

- [OpenCV Camera Calibration](https://docs.opencv.org/master/dc/dbb/tutorial_py_calibration.html)
- [RealSense SDK](https://github.com/IntelRealSense/librealsense)
- [RPLidar SDK](https://github.com/Slamtec/rplidar_sdk)
