import numpy as np
import cv2
import pyrealsense2 as rs
import math
import os
import time
from rplidar import RPLidar

# ==============================
# CONFIG
# ==============================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALIB_FILE = os.path.join(PROJECT_ROOT, "calibration_result_pnp.npz")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "fusion_output")
PORT = "COM3"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================
# LOAD CALIBRATION
# ==============================
data = np.load(CALIB_FILE)
K = data["K"]
R = data["R"]
T = data["T"]

print("Loaded calibration")

# ==============================
# INIT CAMERA
# ==============================
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

profile = pipeline.start(config)
align = rs.align(rs.stream.color)

# ==============================
# INIT LIDAR
# ==============================
lidar = RPLidar(PORT)

def polar_to_cartesian(angle_deg, dist):
    angle_rad = math.radians(angle_deg)
    x = dist * math.sin(angle_rad)
    z = dist * math.cos(angle_rad)
    return x, z

# ==============================
# MAIN LOOP
# ==============================
save_id = 0

try:
    for scan in lidar.iter_scans():

        # ===== CAMERA =====
        frames = pipeline.wait_for_frames()
        aligned = align.process(frames)

        depth_frame = aligned.get_depth_frame()
        color_frame = aligned.get_color_frame()

        if not depth_frame or not color_frame:
            continue

        color_img = np.asanyarray(color_frame.get_data())
        depth_img = np.asanyarray(depth_frame.get_data())

        overlay = color_img.copy()

        # ===== LIDAR → PROJECT =====
        for q, angle, dist in scan:

            if dist == 0:
                continue

            # chỉ lấy phía trước
            if angle > 180:
                angle -= 360
            if not (-90 <= angle <= 90):
                continue

            x, z = polar_to_cartesian(angle, dist)

            lidar_pt = np.array([[x], [0], [z]])

            # transform
            cam_pt = R @ lidar_pt + T

            Xc, Yc, Zc = cam_pt.flatten()

            if Zc <= 0:
                continue

            # project
            u = int(K[0,0]*Xc/Zc + K[0,2])
            v = int(K[1,1]*Yc/Zc + K[1,2])

            # check frame
            if 0 <= u < 640 and 0 <= v < 480:
                cv2.circle(overlay, (u, v), 2, (0,255,0), -1)

        # ===== DEPTH COLORMAP =====
        depth_cm = cv2.applyColorMap(
            cv2.convertScaleAbs(depth_img, alpha=0.03),
            cv2.COLORMAP_JET
        )

        # ===== STACK VIEW =====
        combined = np.hstack((overlay, depth_cm))

        cv2.imshow("Fusion (Color + Depth)", combined)

        key = cv2.waitKey(1) & 0xFF

        # ===== SAVE =====
        if key == ord('s'):
            ts = int(time.time()*1000)

            cv2.imwrite(os.path.join(OUTPUT_DIR, f"color_{ts}.png"), color_img)
            cv2.imwrite(os.path.join(OUTPUT_DIR, f"depth_{ts}.png"), depth_img)
            cv2.imwrite(os.path.join(OUTPUT_DIR, f"fusion_{ts}.png"), overlay)

            print(f"Saved {ts}")
            save_id += 1

        if key == ord('q'):
            break

finally:
    lidar.stop()
    lidar.disconnect()
    pipeline.stop()
    cv2.destroyAllWindows()