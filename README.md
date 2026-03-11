# LiDAR-Camera Sensor Fusion

Hệ thống calibration và fusion **RPLidar A1M8** (2D LiDAR) với **Intel RealSense D435** (RGB-D Camera), sử dụng phương pháp **Homography + RANSAC**.

## Yêu cầu

### Phần cứng
- RPLidar A1M8 (kết nối COM3)
- Intel RealSense D435 (USB 3.0)
- Thanh target (thanh phẳng, bề mặt phản xạ tốt, dễ nhận diện trên cả LiDAR và camera)

### Phần mềm
```bash
pip install pyrealsense2 numpy opencv-python rplidar-roboticia matplotlib keyboard
```

## Cấu trúc project

```
LiDAR-Camera-Fusion/
│
├── src/
│   ├── collect_calibration.py      # Bước 1: Thu thập dữ liệu calibration
│   ├── compute_calibration.py      # Bước 2: Tính ma trận Homography
│   └── fusion_calibration.py       # Bước 3: Fusion real-time (RGB + Depth)
│
├── data/
│   ├── captured_data/              # Dữ liệu thu thập
│   │   ├── calibration/            # File JSON calibration
│   │   ├── color/                  # Ảnh RGB
│   │   ├── depth/                  # Ảnh depth raw
│   │   └── depth_colormap/         # Ảnh depth dạng màu
│   │
│   └── fusion_output/              # Ảnh fusion đã lưu (tự sinh)
│       ├── color/                  # RGB + LiDAR overlay
│       └── depth/                  # Depth + LiDAR overlay
│
├── calibration_result.npz          # Kết quả calibration (tự sinh)
├── lidar_data.csv                  # Log dữ liệu LiDAR
└── README.md
```

## Hướng dẫn sử dụng

### Bước 1: Thu thập dữ liệu

```bash
python src/collect_calibration.py
```

1. Đặt thanh target phía trước camera + LiDAR
2. Biểu đồ **polar** hiển thị LiDAR real-time
3. Nhấn **S** để bắt đầu calibration:
   - **Scatter plot** hiện lên → click chọn **2 đầu thanh** trên dữ liệu LiDAR → nhấn **Enter**
   - **Ảnh RGB** hiện lên → click chọn **2 đầu thanh** trên ảnh camera → nhấn **Enter**
   - Xem kết quả mapping → nhấn **Enter** để xác nhận lưu
4. Di chuyển thanh target đến vị trí/khoảng cách khác, nhấn **S** lại
5. Thu thập **ít nhất 4–6 lần** ở các khoảng cách khác nhau (0.5m → 2m)
6. Nhấn **Ctrl+C** để thoát

Dữ liệu lưu tại `data/captured_data/calibration/calibration_*.json`.

### Bước 2: Tính Homography

```bash
python src/compute_calibration.py
```

1. Load tất cả file JSON từ `data/captured_data/calibration/`
2. Chuyển LiDAR polar → Cartesian: `x = dist × sin(θ)`, `z = dist × cos(θ)`
3. Tính ma trận Homography H (3×3) bằng `cv2.findHomography` + RANSAC (ngưỡng 5.0 px)
4. In reprojection error (mean, median, max, std)
5. Hiển thị ảnh so sánh: **xanh lá** = ground truth, **đỏ** = projected
6. Lưu kết quả vào `calibration_result.npz`

**Kết quả tốt:** Mean error < 10 px

### Bước 3: Fusion real-time

```bash
python src/fusion_calibration.py
```

Hiển thị **1 cửa sổ** ghép RGB và Depth cạnh nhau, LiDAR points phủ lên cả hai:
- Xanh lá = gần (≤ 300 mm)
- Vàng = trung bình
- Đỏ = xa (≥ 4000 mm)
- Nhấn **S** → lưu 2 ảnh vào `data/fusion_output/color/` và `data/fusion_output/depth/`
- Nhấn **Q** để thoát

## Nguyên lý hoạt động

### Hệ tọa độ LiDAR
- Dữ liệu gốc: tọa độ cực **(góc°, khoảng cách mm)**
- Góc 0°–360° → chuẩn hóa về −180° đến +180°, lọc giữ ±90°
- Chuyển sang Cartesian: `x = dist × sin(θ)`, `z = dist × cos(θ)`
  - x: ngang (dương = phải, âm = trái)
  - z: sâu (hướng phía trước)

### Homography

Ma trận H (3×3) ánh xạ từ tọa độ Cartesian LiDAR 2D sang pixel camera 2D:

```
⎡u'⎤       ⎡x⎤
⎢v'⎥ = H × ⎢z⎥
⎣w ⎦       ⎣1⎦

u = u'/w,   v = v'/w
```

Sử dụng trong code:
```python
H = np.load('calibration_result.npz')['homography']

x = distance * math.sin(math.radians(angle))
z = distance * math.cos(math.radians(angle))

pt = np.array([x, z, 1.0])
pixel = H @ pt
u, v = int(pixel[0] / pixel[2]), int(pixel[1] / pixel[2])
```

### Nội suy tuyến tính (Linear Interpolation)

Khi thu thập dữ liệu, ánh xạ điểm LiDAR trên thanh → pixel bằng nội suy:

```
t = (θ − θ_min) / (θ_max − θ_min)
u = u₁ + t × (u₂ − u₁)
v = v₁ + t × (v₂ − v₁)
```

## Troubleshooting

| Vấn đề | Giải pháp |
|---------|-----------|
| LiDAR không kết nối | Kiểm tra COM port trong Device Manager |
| Camera timeout | Rút cắm lại USB, đảm bảo USB 3.0 |
| Error cao (> 20 px) | Thu thập thêm dữ liệu ở nhiều khoảng cách hơn |
| Fusion bị đơ | Đóng các app khác dùng camera/LiDAR |

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
=======
## Hướng dẫn sử dụng collect.py

### Tổng quan
`collect.py` là script Python dùng để thu thập và trực quan hóa dữ liệu từ cảm biến RPLidar và camera Intel RealSense. Script này cho phép hiển thị dữ liệu quét LiDAR theo thời gian thực, lưu dữ liệu vào file CSV, đồng thời chụp ảnh màu và ảnh sâu từ RealSense khi người dùng nhấn phím.

### Tính năng chính
- Kết nối và lấy dữ liệu từ RPLidar, hiển thị lên biểu đồ cực (polar plot).
- Kết nối và chụp ảnh từ camera RealSense (ảnh màu, ảnh sâu, ảnh sâu dạng colormap).
- Lưu dữ liệu quét LiDAR vào file CSV, lưu ảnh vào thư mục riêng khi nhấn phím `s`.
- Hiển thị trực quan dữ liệu LiDAR theo thời gian thực bằng matplotlib.

### Yêu cầu
- Python 3.x
- Các thư viện: rplidar, pyrealsense2, matplotlib, numpy, opencv-python, keyboard

Cài đặt nhanh:
```bash
pip install rplidar pyrealsense2 matplotlib numpy opencv-python keyboard
```

### Cách sử dụng
1. Kết nối RPLidar và RealSense vào máy tính.
2. Chỉnh sửa biến `PORT` trong script cho đúng với cổng serial của RPLidar (ví dụ: `COM3`).
3. Chạy script:
	 ```bash
	 python collect.py
	 ```
4. Nhấn phím `s` để lưu dữ liệu quét LiDAR hiện tại và chụp ảnh từ RealSense.
5. Dữ liệu sẽ được lưu vào file `lidar_data.csv` và ảnh vào thư mục `captured_data`.
6. Nhấn `Ctrl+C` để thoát chương trình.

### Kết quả
- **File CSV:** `lidar_data.csv` chứa dữ liệu quét LiDAR kèm timestamp (góc, khoảng cách).
- **Ảnh:**
	- `captured_data/color/`: Ảnh màu từ RealSense.
	- `captured_data/depth/`: Ảnh sâu (depth).
	- `captured_data/depth_colormap/`: Ảnh sâu dạng colormap.

### Lưu ý
- Đảm bảo đã cài đủ các thư viện Python cần thiết.
- Script phù hợp cho Windows (dùng thư viện `keyboard` để nhận phím).
- Có thể cần quyền admin để sử dụng thư viện `keyboard`.

### Bản quyền
Script này phục vụ mục đích nghiên cứu và giáo dục, sử dụng tự do.
# DepthCompletion_SensorFusion
A low-cost depth completion system based on sensor fusion between a single-line LiDAR and an RGB camera, using deep learning to generate dense and accurate depth maps.
>>>>>>> 2800b44b53970861c7ca7c30d376b4af3bf892c7
