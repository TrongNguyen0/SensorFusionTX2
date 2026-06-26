# SensorFusionTX2

PyQt-based Camera-LiDAR sensor fusion demo using an Intel RealSense camera and an RPLidar sensor.

## Repository Structure

```text
src/   Source code for data collection, calibration, fusion, and the PyQt UI
data/  Captured calibration data, calibration results, and fusion output samples
```

## Main Features

- Collect synchronized RealSense RGB/depth frames and RPLidar scans.
- Select calibration correspondences between LiDAR target points and camera image points.
- Compute camera-LiDAR calibration parameters `K`, `R`, and `t`.
- Project LiDAR points onto the camera image for real-time fusion visualization.
- Browse captured data, calibration previews, and fusion output from the PyQt interface.

## Main Entry Point

Run the PyQt application:

```bash
python src/app_pyqt.py
```

## Calibration Workflow

1. Open the UI and select `Collect`.
2. Start camera and LiDAR sensors.
3. Capture calibration samples.
4. Select corresponding LiDAR and image points.
5. Accept valid samples.
6. Switch to `Compute` and run calibration.
7. Switch to `Fusion` and start real-time projection.

## Hardware Notes

- Camera: Intel RealSense D435
- LiDAR: RPLidar A1M8
- LiDAR connection: UART through USB serial, configured as `COM3` by default

## Dependencies

The application uses Python with:

- PyQt5
- OpenCV
- NumPy
- pyrealsense2
- rplidar

Install dependencies according to the active Python environment before running the UI.
