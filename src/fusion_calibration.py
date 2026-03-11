from rplidar import RPLidar
import math
import pyrealsense2 as rs
import numpy as np
import cv2
import threading
import time
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PORT = "COM3"
CALIBRATION_FILE = os.path.join(PROJECT_ROOT, "calibration_result.npz")
SAVE_DIR = os.path.join(PROJECT_ROOT, "data", "fusion_output")

# lidar scan shared between threads
scan_lock = threading.Lock()
latest_scan = []
running = True

def normalize_angle(angle):
    if angle > 180:
        return angle - 360
    return angle

def load_calibration():
    if not os.path.exists(CALIBRATION_FILE):
        print(f"Missing {CALIBRATION_FILE}! Run compute_calibration.py first.")
        sys.exit(1)

    data = np.load(CALIBRATION_FILE)

    if 'homography' not in data:
        print("No homography matrix found in calibration file!")
        sys.exit(1)

    H = data['homography']
    error = float(data['homography_error'])
    print(f"Loaded Homography (error: {error:.2f} px)")
    return H

def lidar_to_pixel(angle_deg, distance_mm, H):
    """Convert lidar (angle, distance) to pixel (u, v) using Homography"""
    angle_rad = math.radians(angle_deg)
    x = distance_mm * math.sin(angle_rad)
    z = distance_mm * math.cos(angle_rad)

    pt = np.array([x, z, 1.0])
    pixel = H @ pt
    if abs(pixel[2]) < 1e-6:
        return None
    return int(pixel[0] / pixel[2]), int(pixel[1] / pixel[2])

def dist_to_color(dist_mm, min_d=300, max_d=4000):
    """Green (near) -> Yellow -> Red (far)"""
    ratio = np.clip((dist_mm - min_d) / (max_d - min_d), 0, 1)
    if ratio < 0.5:
        r = int(255 * ratio * 2)
        g = 255
    else:
        r = 255
        g = int(255 * (1 - (ratio - 0.5) * 2))
    return (0, g, r)  # BGR

def lidar_thread():
    global latest_scan, running
    try:
        lidar = RPLidar(PORT, baudrate=115200, timeout=3)
        print(f"LiDAR connected on {PORT}")

        for scan in lidar.iter_scans():
            if not running:
                break

            # filter to +-90 degrees
            filtered = []
            for q, angle, dist in scan:
                norm = normalize_angle(angle)
                if -90 <= norm <= 90 and dist > 0:
                    filtered.append((norm, dist))

            with scan_lock:
                latest_scan = filtered

        lidar.stop()
        lidar.disconnect()
    except Exception as e:
        print(f"LiDAR error: {e}")

def init_realsense():
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    profile = pipeline.start(config)
    align = rs.align(rs.stream.color)
    return pipeline, align

def main():
    global running

    color_dir = os.path.join(SAVE_DIR, "color")
    depth_dir = os.path.join(SAVE_DIR, "depth")
    os.makedirs(color_dir, exist_ok=True)
    os.makedirs(depth_dir, exist_ok=True)
    
    # load calibration
    H = load_calibration()

    # start lidar in background
    t = threading.Thread(target=lidar_thread, daemon=True)
    t.start()

    # start camera
    pipeline, align = init_realsense()
    # let camera warm up
    for _ in range(30):
        pipeline.wait_for_frames(timeout_ms=5000)

    os.makedirs(SAVE_DIR, exist_ok=True)
    save_count = 0
    print("Starting fusion. Press 's' to save, 'q' to quit.")

    try:
        while True:
            # get camera frame
            frames = pipeline.wait_for_frames(timeout_ms=10000)
            aligned = align.process(frames)
            color_frame = aligned.get_color_frame()
            depth_frame = aligned.get_depth_frame()

            if not color_frame or not depth_frame:
                continue

            color_img = np.asanyarray(color_frame.get_data())
            depth_colormap = cv2.applyColorMap(
                cv2.convertScaleAbs(np.asanyarray(depth_frame.get_data()), alpha=0.03),
                cv2.COLORMAP_JET
            )
            frame_rgb = color_img.copy()
            frame_depth = depth_colormap.copy()

            # get current lidar scan
            with scan_lock:
                scan = list(latest_scan)

            # project lidar points onto both images
            count = 0
            for angle, dist in scan:
                result = lidar_to_pixel(angle, dist, H)
                if result is None:
                    continue

                u, v = result

                if 0 <= u < 640 and 0 <= v < 480:
                    color = dist_to_color(dist)
                    cv2.circle(frame_rgb, (u, v), 4, color, -1)
                    cv2.circle(frame_depth, (u, v), 4, color, -1)
                    count += 1

            info = f"LiDAR: {count}/{len(scan)}"
            hint = "s: save | q: quit"
            for img in (frame_rgb, frame_depth):
                cv2.putText(img, info, (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(img, hint, (10, 470),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            # combine side by side in one window
            combined = np.hstack((frame_rgb, frame_depth))
            cv2.imshow("LiDAR Fusion | RGB - Depth", combined)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('s'):
                save_count += 1
                ts = int(time.time() * 1000)
                cv2.imwrite(os.path.join(color_dir, f"rgb_lidar_{ts}.png"), frame_rgb)
                cv2.imwrite(os.path.join(depth_dir, f"depth_lidar_{ts}.png"), frame_depth)
                print(f"[{save_count}] Saved to {SAVE_DIR}/ (ts={ts})")
            elif key == ord('q'):
                break

    except KeyboardInterrupt:
        pass
    finally:
        running = False
        pipeline.stop()
        cv2.destroyAllWindows()
        print("Done.")

if __name__ == "__main__":
    main()
