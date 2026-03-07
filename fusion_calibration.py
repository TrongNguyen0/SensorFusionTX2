from rplidar import RPLidar
import math
import pyrealsense2 as rs
import numpy as np
import cv2
import threading
import time
import os
import sys

PORT = "COM3"
CALIBRATION_FILE = "calibration_result.npz"

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

    data = np.load(CALIBRATION_FILE, allow_pickle=True)
    method = str(data['best_method'])
    print(f"Loaded calibration: best method = {method}")

    H = data['homography'] if 'homography' in data else None
    A = data['affine'] if 'affine' in data else None

    # pick the best one
    if method == 'homography' and H is not None:
        print(f"  Using Homography (error: {data['homography_error']:.2f} px)")
        return 'homography', H
    elif method == 'affine' and A is not None:
        print(f"  Using Affine (error: {data['affine_error']:.2f} px)")
        return 'affine', A
    elif H is not None:
        print(f"  Fallback to Homography")
        return 'homography', H
    elif A is not None:
        print(f"  Fallback to Affine")
        return 'affine', A
    else:
        print("No usable calibration found!")
        sys.exit(1)

def lidar_to_pixel(angle_deg, distance_mm, method, matrix):
    """Convert lidar (angle, distance) to pixel (u, v) using calibration"""
    angle_rad = math.radians(angle_deg)
    x = distance_mm * math.sin(angle_rad)
    z = distance_mm * math.cos(angle_rad)

    if method == 'homography':
        pt = np.array([x, z, 1.0])
        pixel = matrix @ pt
        if abs(pixel[2]) < 1e-6:
            return None
        u = pixel[0] / pixel[2]
        v = pixel[1] / pixel[2]
    elif method == 'affine':
        pt = np.array([x, z, 1.0])
        pixel = matrix @ pt
        u = pixel[0]
        v = pixel[1]
    else:
        return None

    return int(u), int(v)

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

    # load calibration
    method, matrix = load_calibration()

    # start lidar in background
    t = threading.Thread(target=lidar_thread, daemon=True)
    t.start()

    # start camera
    pipeline, align = init_realsense()
    print("Starting fusion. Press 'q' to quit.")

    try:
        while True:
            # get camera frame
            frames = pipeline.wait_for_frames(timeout_ms=5000)
            aligned = align.process(frames)
            color_frame = aligned.get_color_frame()
            depth_frame = aligned.get_depth_frame()

            if not color_frame:
                continue

            color_img = np.asanyarray(color_frame.get_data())
            frame = color_img.copy()

            # get current lidar scan
            with scan_lock:
                scan = list(latest_scan)

            # project lidar points onto image
            count = 0
            for angle, dist in scan:
                result = lidar_to_pixel(angle, dist, method, matrix)
                if result is None:
                    continue

                u, v = result

                # check bounds
                if 0 <= u < 640 and 0 <= v < 480:
                    color = dist_to_color(dist)
                    cv2.circle(frame, (u, v), 4, color, -1)
                    count += 1

            # info text
            cv2.putText(frame, f"LiDAR points: {count}/{len(scan)}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, f"Method: {method}", (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, "q: quit", (10, 470),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            cv2.imshow("LiDAR + Camera Fusion", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
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
