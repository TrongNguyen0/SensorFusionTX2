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
