from rplidar import RPLidar
import math
import matplotlib.pyplot as plt
import time 
import csv
import keyboard
import pyrealsense2 as rs
import numpy as np
import cv2
import os
import json
import threading

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PORT = "COM3"
CSV_FILE = os.path.join(PROJECT_ROOT, "lidar_data.csv")
PLOT_UPDATE_INTERVAL = 0.2
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "captured_data")

clicked_points = []
click_image = None

# shared lidar data
scan_lock = threading.Lock()
latest_filtered = []
lidar_running = True

def normalize_angle(angle):
    if angle > 180:
        return angle - 360
    return angle

def filter_scan(scan_data):
    filtered = []
    for q, angle, dist in scan_data:
        norm = normalize_angle(angle)
        if -90 <= norm <= 90 and dist > 0:
            filtered.append((q, norm, dist))
    filtered.sort(key=lambda x: x[1])
    return filtered

def init_lidar():    
    print("Initializing LIDAR...")
    lidar = RPLidar(PORT, baudrate=115200, timeout=3)
    info = lidar.get_info()
    print(f"LIDAR Info: {info}")
    health = lidar.get_health()
    print(f"LIDAR Health: {health}")
    return lidar

def init_realsense():
    print("Initializing RealSense Camera...")
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    profile = pipeline.start(config)
    align = rs.align(rs.stream.color)
    return pipeline, align

def init_plot():
    plt.ion()
    fig, ax = plt.subplots(subplot_kw={'projection': 'polar'})
    ax.set_ylim(0, 6000)
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_thetamin(-90)
    ax.set_thetamax(90)
    ax.set_title("RPLidar +-90")
    line, = ax.plot([], [], 'b.', markersize=1)

    # move polar window to top-left
    try:
        fig.canvas.manager.window.wm_geometry("+50+50")
    except:
        pass

    return fig, ax, line

def init_csv(file_name):
    f = open(file_name, mode='w', newline='')
    writer = csv.writer(f)
    writer.writerow(['Time', 'Angle', 'Distance'])
    return f, writer

def lidar_thread(lidar):
    """Background thread: continuously read lidar scans"""
    global latest_filtered, lidar_running
    try:
        for scan in lidar.iter_scans():
            if not lidar_running:
                break
            filtered = filter_scan(scan)
            with scan_lock:
                latest_filtered = filtered
    except Exception as e:
        print(f"LiDAR thread error: {e}")

def get_scan():
    """Get a copy of latest filtered scan"""
    with scan_lock:
        return list(latest_filtered)

def update_polar(ax, line, fig, count):
    """Update polar plot with latest scan data"""
    scan = get_scan()
    if len(scan) == 0:
        return
    try:
        angles = [math.radians(a) for _, a, _ in scan]
        dists = [d for _, _, d in scan]
        line.set_data(angles, dists)
        ax.set_title(f'LiDAR - Saved: {count} - Points: {len(scan)}')
        fig.canvas.draw_idle()
        fig.canvas.flush_events()
    except:
        pass

def save_csv(writer, scan, timestamp):
    for _, angle, dist in scan:
        if dist > 0:
            writer.writerow([timestamp, round(angle, 2), int(dist)])

def mouse_cb(event, x, y, flags, param):
    global clicked_points, click_image
    if event == cv2.EVENT_LBUTTONDOWN and len(clicked_points) < 2:
        clicked_points.append((x, y))  #them pixel vao list
        color = (0, 255, 0) if len(clicked_points) == 1 else (0, 0, 255)
        cv2.circle(click_image, (x, y), 5, color, -1)
        cv2.putText(click_image, f"P{len(clicked_points)}", (x+10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        cv2.imshow("Select Points", click_image)
        print(f"  P{len(clicked_points)}: ({x}, {y})")

def select_bar_points(scan_data, polar_ax, polar_line, polar_fig, count):
    """Show scatter of lidar points, click P1 and P2 of bar, enter to confirm.
    Polar plot keeps updating in the background."""
    if len(scan_data) == 0:
        return None

    angles = [a for _, a, _ in scan_data]
    dists = [d for _, _, d in scan_data]
    selected = []

    fig2, ax2 = plt.subplots(figsize=(10, 5), num="LiDAR Points")
    ax2.scatter(angles, dists, c='blue', s=10)
    ax2.set_xlabel('Angle')
    ax2.set_ylabel('Distance (mm)')
    ax2.set_title('Click P1 (left) and P2 (right) of the bar, then Enter')
    ax2.grid(True)

    try:
        fig2.canvas.manager.window.wm_geometry("+700+50")
    except:
        pass

    def on_click(event):
        if event.inaxes != ax2 or len(selected) >= 2:
            return

        a_range = max(angles) - min(angles) if max(angles) != min(angles) else 1
        d_range = max(dists) - min(dists) if max(dists) != min(dists) else 1

        best_i = 0
        best_d = float('inf')
        for i, (a, d) in enumerate(zip(angles, dists)):
            dist_sq = ((a - event.xdata) / a_range)**2 + ((d - event.ydata) / d_range)**2
            if dist_sq < best_d:
                best_d = dist_sq
                best_i = i

        selected.append(best_i)
        color = 'green' if len(selected) == 1 else 'red'
        ax2.scatter(angles[best_i], dists[best_i], c=color, s=100, zorder=5, marker='x', linewidths=3)
        ax2.annotate(f'P{len(selected)}: ({angles[best_i]:.1f}, {dists[best_i]:.0f})',
                     (angles[best_i], dists[best_i]),
                     textcoords="offset points", xytext=(10, 10), fontsize=9, color=color)

        if len(selected) == 2:
            ax2.set_title('Done! Press Enter to continue')
        fig2.canvas.draw()

    def on_key(event):
        if event.key == 'enter' and len(selected) == 2:
            plt.close(fig2)

    fig2.canvas.mpl_connect('button_press_event', on_click)
    fig2.canvas.mpl_connect('key_press_event', on_key)

    # wait for scatter to close, keep polar alive
    last_update = time.time()
    while plt.fignum_exists(fig2.number):
        plt.pause(0.05)
        now = time.time()
        if now - last_update >= PLOT_UPDATE_INTERVAL:
            update_polar(polar_ax, polar_line, polar_fig, count)
            last_update = now

    if len(selected) < 2:
        return None

    # get angle range from selected indices
    a1 = angles[selected[0]]
    a2 = angles[selected[1]]
    start = min(a1, a2)
    end = max(a1, a2)

    bar = [(q, a, d) for q, a, d in scan_data if start <= a <= end]
    bar.sort(key=lambda x: x[1])

    print(f"  Bar range: {start:.1f} to {end:.1f} ({len(bar)} points)")
    return bar

def capture_frames(pipeline, align):
    frames = pipeline.wait_for_frames(timeout_ms=5000)
    aligned = align.process(frames)
    depth_frame = aligned.get_depth_frame()
    color_frame = aligned.get_color_frame()
    if not depth_frame or not color_frame:
        return None, None
    depth_img = np.asanyarray(depth_frame.get_data())
    color_img = np.asanyarray(color_frame.get_data())
    return color_img, depth_img

def select_image_points(color_img, polar_ax, polar_line, polar_fig, count):
    """Show RGB image, click P1 and P2 on bar, enter to confirm"""
    global clicked_points, click_image
    clicked_points = []
    click_image = color_img.copy()

    print("\n--- Click P1 (left) and P2 (right) on the bar, then Enter ---")

    cv2.namedWindow("Select Points")
    cv2.moveWindow("Select Points", 700, 50)
    cv2.setMouseCallback("Select Points", mouse_cb)
    cv2.imshow("Select Points", click_image)

    last_update = time.time()
    while True:
        key = cv2.waitKey(30) & 0xFF
        if key == ord('q'):
            cv2.destroyWindow("Select Points")
            return None, None
        if key == 13 and len(clicked_points) == 2:
            break
        # keep polar alive
        now = time.time()
        if now - last_update >= PLOT_UPDATE_INTERVAL:
            update_polar(polar_ax, polar_line, polar_fig, count)
            last_update = now

    cv2.destroyWindow("Select Points")
    return clicked_points[0], clicked_points[1]

def map_lidar_to_image(bar_points, p1, p2):
    """Map bar lidar points onto the line P1-P2"""
    angles = [a for _, a, _ in bar_points]
    min_a = min(angles)
    max_a = max(angles)

    mapped = []
    for _, angle, dist in bar_points:
        if max_a != min_a:
            t = (angle - min_a) / (max_a - min_a)
        else:
            t = 0.5
        px = int(p1[0] + t * (p2[0] - p1[0]))
        py = int(p1[1] + t * (p2[1] - p1[1]))
        mapped.append({'angle': angle, 'distance': dist, 'pixel_x': px, 'pixel_y': py})
    return mapped

def show_result(color_img, mapped_points, p1, p2, polar_ax, polar_line, polar_fig, count):
    """Show image with mapped lidar points, enter to continue"""
    result = color_img.copy()
    cv2.line(result, p1, p2, (255, 255, 0), 2)
    for pt in mapped_points:
        cv2.circle(result, (pt['pixel_x'], pt['pixel_y']), 3, (0, 255, 0), -1)

    cv2.namedWindow("Result")
    cv2.moveWindow("Result", 700, 50)
    cv2.imshow("Result", result)
    print("--- Result shown. Press Enter to continue ---")

    last_update = time.time()
    while True:
        key = cv2.waitKey(30) & 0xFF
        if key == 13:
            break
        now = time.time()
        if now - last_update >= PLOT_UPDATE_INTERVAL:
            update_polar(polar_ax, polar_line, polar_fig, count)
            last_update = now

    cv2.destroyWindow("Result")
    return result

def save_all(color_img, depth_img, result_img, calibration_data, timestamp):
    """Save images and calibration json"""
    color_dir = os.path.join(OUTPUT_DIR, "color")
    depth_dir = os.path.join(OUTPUT_DIR, "depth")
    depth_cm_dir = os.path.join(OUTPUT_DIR, "depth_colormap")
    calib_dir = os.path.join(OUTPUT_DIR, "calibration")

    for d in [color_dir, depth_dir, depth_cm_dir, calib_dir]:
        os.makedirs(d, exist_ok=True)

    cv2.imwrite(os.path.join(color_dir, f"color_{timestamp}.png"), color_img)
    cv2.imwrite(os.path.join(depth_dir, f"depth_{timestamp}.png"), depth_img)

    depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_img, alpha=0.03), cv2.COLORMAP_JET)
    cv2.imwrite(os.path.join(depth_cm_dir, f"depth_colormap_{timestamp}.png"), depth_colormap)

    cv2.imwrite(os.path.join(calib_dir, f"calibration_{timestamp}.png"), result_img)

    with open(os.path.join(calib_dir, f"calibration_{timestamp}.json"), 'w') as f:
        json.dump(calibration_data, f, indent=2)

    print(f"  Saved to {OUTPUT_DIR}/ (timestamp: {timestamp})")

def calibrate(pipeline, align, scan_data, timestamp, polar_ax, polar_line, polar_fig, count):
    """Full calibration flow: lidar select -> camera select -> map -> save"""

    # capture camera first to avoid timeout
    color_img, depth_img = capture_frames(pipeline, align)
    if color_img is None:
        print("Failed to capture camera frames!")
        return None

    # 1. select bar on lidar scatter
    print("\n--- Select bar points on LiDAR ---")
    bar = select_bar_points(scan_data, polar_ax, polar_line, polar_fig, count)
    if bar is None or len(bar) < 2:
        print("Cancelled or not enough points.")
        return None

    # 2. select P1 P2 on RGB
    p1, p2 = select_image_points(color_img, polar_ax, polar_line, polar_fig, count)
    if p1 is None:
        print("Cancelled.")
        return None

    # 3. map lidar -> image
    mapped = map_lidar_to_image(bar, p1, p2)

    angles = [a for _, a, _ in bar]
    dists = [d for _, _, d in bar]

    calibration_data = {
        'timestamp': timestamp,
        'image_point_start': p1,
        'image_point_end': p2,
        'lidar_angle_min': min(angles),
        'lidar_angle_max': max(angles),
        'lidar_points_count': len(bar),
        'avg_distance': sum(dists) / len(dists),
        'mapped_points': mapped
    }

    # 4. show result
    result_img = show_result(color_img, mapped, p1, p2, polar_ax, polar_line, polar_fig, count)

    # 5. save everything
    save_all(color_img, depth_img, result_img, calibration_data, timestamp)

    return calibration_data

def main_loop(lidar, writer, pipeline, align):
    global lidar_running
    print('Starting main loop. Press "s" to calibrate, Ctrl+C to quit')

    fig, ax, line = init_plot()
    save_count = 0
    save_request = False
    last_plot_time = time.time()

    # start lidar in background thread
    t = threading.Thread(target=lidar_thread, args=(lidar,), daemon=True)
    t.start()

    try:
        while True:
            # update polar plot
            now = time.time()
            if now - last_plot_time >= PLOT_UPDATE_INTERVAL:
                if plt.fignum_exists(fig.number):
                    update_polar(ax, line, fig, save_count)
                last_plot_time = now

            plt.pause(0.05)

            if save_request:
                filtered = get_scan()
                if len(filtered) > 0:
                    timestamp = int(time.time() * 1000)
                    print(f"\n===== Calibration #{save_count + 1} =====")

                    save_csv(writer, filtered, timestamp)
                    result = calibrate(pipeline, align, filtered, timestamp, ax, line, fig, save_count)

                    if result:
                        save_count += 1
                        print(f"-> Done #{save_count}")
                    else:
                        print("-> Skipped")

                save_request = False

            if keyboard.is_pressed('s'):
                save_request = True

    except KeyboardInterrupt:
        print("Interrupted.")
    finally:
        lidar_running = False

def cleanup(lidar, csv_file, pipeline):
    global lidar_running
    lidar_running = False
    time.sleep(0.5)
    csv_file.close()
    try:
        lidar.stop()
        lidar.disconnect()
    except:
        pass
    plt.close('all')
    cv2.destroyAllWindows()
    pipeline.stop()
    print("Cleaned up.")

if __name__ == "__main__":
    lidar = init_lidar()
    pipeline, align = init_realsense()
    csv_file, writer = init_csv(CSV_FILE)
    try:
        main_loop(lidar, writer, pipeline, align)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup(lidar, csv_file, pipeline)