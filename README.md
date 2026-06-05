# SensorFusionTX2

Realtime Sensor Fusion on Jetson TX2 using Intel RealSense RGB-D, RPLidar A1, `pyrplidar`, OpenCV, NumPy, and Python 3.6.

The calibration file is expected at:

```bash
calibration_result_pnp.npz
```

It must contain:

```text
K: 3x3 camera intrinsic matrix
R: 3x3 LiDAR-to-camera rotation matrix
T: 3x1 LiDAR-to-camera translation vector
```

## Project Layout

```text
project_root/
├── src/
│   ├── calibration_loader.py
│   ├── realsense_reader.py
│   ├── lidar_reader.py
│   ├── fusion_engine.py
│   ├── fusion_visualizer.py
│   ├── dataset_logger.py
│   ├── tcp_server.py
│   └── main.py
├── client/
│   └── tcp_client.py
├── calibration_result_pnp.npz
└── README.md
```

## Jetson Requirements

Install the runtime dependencies on Jetson:

```bash
pip3 install numpy opencv-python pyrplidar pyserial
```

`pyrealsense2` should come from the Librealsense build/install used on the Jetson.

The user running the app must have access to `/dev/ttyUSB0`. A persistent fix is to add the user to `dialout` and re-login:

```bash
sudo usermod -aG dialout $USER
```

## Run On Jetson

From the project root:

```bash
python3 src/main.py
```

Useful options:

```bash
python3 src/main.py --no-display
python3 src/main.py --tcp-port 9999
python3 src/main.py --lidar-port /dev/ttyUSB0
python3 src/main.py --scan-mode force
```

Controls when display is enabled:

```text
S       save dataset sample
Q/Esc   quit
```

Saved samples are written to:

```text
dataset/YYYYMMDD_HHMMSS/
├── color.png
├── depth.png
├── fusion.png
├── lidar.npy
└── metadata.json
```

## TCP Visualization Client

On the laptop:

```bash
python3 client/tcp_client.py --host <JETSON_IP> --port 9999
```

Press `Q` or `Esc` in the client window to quit.

## Coordinate Convention

LiDAR polar measurements are converted to LiDAR XYZ in millimeters:

```text
x = distance * sin(angle)
y = 0
z = distance * cos(angle)
```

Then the calibration transform is applied:

```text
CameraXYZ = R * LiDARXYZ + T
```

Projection uses:

```text
uv = K * CameraXYZ
```

Points with invalid LiDAR distance, negative camera depth, or image coordinates outside the color frame are discarded.
