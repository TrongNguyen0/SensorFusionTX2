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
import statistics

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PORT = "COM3"
CSV_FILE = os.path.join(PROJECT_ROOT, "lidar_data.csv")
PLOT_UPDATE_INTERVAL = 0.2
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "captured_data")
COLOR_WIDTH = 640
COLOR_HEIGHT = 480
DEPTH_WIDTH = 640
DEPTH_HEIGHT = 480
CAMERA_FPS = 30
FRONT_ANGLE_MIN = -90
FRONT_ANGLE_MAX = 90
DENOISE_SCAN_COUNT = 10
BAR_DISTANCE_JUMP_THRESHOLD_MM = 300

clicked_points = []
click_image = None

# shared lidar data
scan_lock = threading.Lock()
latest_filtered = []
lidar_running = True
scans_buffer = []  # Buffer tích lũy các scan để lọc nhiễu

def normalize_angle(angle):
    if angle > 180:
        return angle - 360
    return angle

def filter_scan(scan_data):
    filtered = []
    for q, angle, dist in scan_data:
        norm = normalize_angle(angle)
        if FRONT_ANGLE_MIN <= norm <= FRONT_ANGLE_MAX and dist > 0:
            filtered.append((q, norm, dist))
    filtered.sort(key=lambda x: x[1])
    return filtered

def denoise_lidar_scans(num_scans=10):
    """
    Lọc nhiễu dữ liệu LiDAR từ buffer.
    - Dùng num_scans scan gần nhất từ buffer
    - Làm tròn góc đến độ nguyên gần nhất
    - Tính trung bình khoảng cách cho mỗi góc
    """
    global scans_buffer, scan_lock
    
    angle_dist_map = {}  # key: angle_rounded, value: list of distances
    
    with scan_lock:
        scans_to_use = scans_buffer[-num_scans:] if len(scans_buffer) >= num_scans else list(scans_buffer)
        scans_buffer = scans_buffer[-num_scans:]     # giữ lại dữ liệu, không xóa sạch
    
    if len(scans_to_use) == 0:
        print("  No scan data available!")
        return []
    
    print(f"  Denoising using {len(scans_to_use)} scans...")
    
    for scan in scans_to_use:
        for q, angle, dist in scan:
            # Làm tròn góc đến độ nguyên gần nhất
            angle_rounded = round(angle)
            
            if angle_rounded not in angle_dist_map:
                angle_dist_map[angle_rounded] = []
            angle_dist_map[angle_rounded].append(dist)
    
    if len(angle_dist_map) == 0:
        print("  No data after denoising!")
        return []
    
    # Tính trung bình khoảng cách cho mỗi góc
    denoised = []
    for angle_rounded in sorted(angle_dist_map.keys()):
        distances = angle_dist_map[angle_rounded]
        avg_dist = statistics.median(distances)
        denoised.append((0, angle_rounded, avg_dist))
    
    print(f"  Denoised points: {len(denoised)} (from {len(scans_to_use)} scans)")
    return denoised

def polar_to_cartesian(angle_deg, distance_mm):
    """
    Chuyển tọa độ cực sang Cartesian
    - angle: độ (-90 đến 90)
    - distance: mm
    - Returns: (x, z) trong mm
      x: ngang (dương=phải, âm=trái)
      z: sâu (hướng phía trước)
    """
    angle_rad = math.radians(angle_deg)
    x = distance_mm * math.sin(angle_rad)
    z = distance_mm * math.cos(angle_rad)
    return x, z

def select_bar_points_polar(scan_data, polar_ax, polar_line, polar_fig, count):
    """
    Chọn 2 điểm thanh trên polar plot (đã lọc nhiễu)
    - click trực tiếp trên polar
    - dùng tọa độ Cartesian để mapping
    """
    if len(scan_data) == 0:
        return None

    # Chuẩn bị dữ liệu
    angles = [a for _, a, _ in scan_data]
    dists = [d for _, _, d in scan_data]
    selected = []
    selected_points = []  # (angle, dist, x, z)

    # Tạo polar plot mới để chọn
    fig2, ax2 = plt.subplots(figsize=(10, 8), subplot_kw={'projection': 'polar'}, num="Select Bar Points")
    ax2.set_ylim(0, 6000)
    ax2.set_theta_zero_location('N')
    ax2.set_theta_direction(-1)
    ax2.set_thetamin(-90)
    ax2.set_thetamax(90)
    
    # Vẽ các điểm
    angles_rad = [math.radians(a) for a in angles]
    ax2.scatter(angles_rad, dists, c='blue', s=10)
    ax2.set_title('Click P1 (left) and P2 (right) on the bar, then Enter')
    ax2.grid(True)

    try:
        fig2.canvas.manager.window.wm_geometry("+700+50")
    except:
        pass

    def on_click(event):
        if event.inaxes != ax2 or len(selected) >= 2:
            return

        # Tìm điểm gần nhất
        if event.xdata is None or event.ydata is None:
            return

        click_x = event.ydata * math.sin(event.xdata)
        click_z = event.ydata * math.cos(event.xdata)

        best_i = 0
        best_d = float('inf')
        
        for i, (theta, r) in enumerate(zip(angles_rad, dists)):
            x = r * math.sin(theta)
            z = r * math.cos(theta)

            dx = x - click_x
            dz = z - click_z
            d = dx*dx + dz*dz
            
            if d < best_d:
                best_d = d
                best_i = i

        selected.append(best_i)
        angle = angles[best_i]
        dist = dists[best_i]
        x, z = polar_to_cartesian(angle, dist)
        selected_points.append((angle, dist, x, z))
        
        color = 'green' if len(selected) == 1 else 'red'
        theta_rad = math.radians(angle)
        ax2.scatter(theta_rad, dist, c=color, s=100, zorder=5, marker='x', linewidths=3)
        ax2.annotate(f'P{len(selected)}: A={angle:.0f}°, D={dist:.0f}mm',
                     (theta_rad, dist),
                     textcoords="offset points", xytext=(10, 10), fontsize=9, color=color)

        if len(selected) == 2:
            ax2.set_title('Done! Press Enter to continue')
        fig2.canvas.draw()

    done_selecting = False

    def on_key(event):
        nonlocal done_selecting
        if event.key == 'enter' and len(selected) == 2:
            done_selecting = True  

    fig2.canvas.mpl_connect('button_press_event', on_click)
    fig2.canvas.mpl_connect('key_press_event', on_key)

    last_update = time.time()
    while plt.fignum_exists(fig2.number) and not done_selecting:
        plt.pause(0.05)
        now = time.time()
        if now - last_update >= PLOT_UPDATE_INTERVAL:
            update_polar(polar_ax, polar_line, polar_fig, count)
            last_update = now

    # Đóng cửa sổ ở NGOÀI vòng lặp sự kiện
    if done_selecting:
        plt.close(fig2)

    if len(selected) < 2:
        return None

    # Lấy dãy điểm thanh
    a1 = angles[selected[0]]
    a2 = angles[selected[1]]
    start = min(a1, a2)
    end = max(a1, a2)

    bar = [(q, a, d) for q, a, d in scan_data if start <= a <= end]
    bar.sort(key=lambda x: x[1])

    clean_bar = []
    prev_dist = None
    for q, a, d in bar:
        if prev_dist is None or abs(d - prev_dist) < BAR_DISTANCE_JUMP_THRESHOLD_MM:
            clean_bar.append((q, a, d))
            prev_dist = d

    bar = clean_bar

    print(f"  Bar range: {start:.0f}° to {end:.0f}° ({len(bar)} points)")
    for i, (a, d, x, z) in enumerate(selected_points):
        x, z = polar_to_cartesian(a, d)
        print(f"    P{i+1}: angle={a:.0f}°, dist={d:.0f}mm, cartesian=({x:.0f}, {z:.0f})")
    
    return bar

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
    ctx = rs.context()
    devices = ctx.query_devices()
    if len(devices) == 0:
        raise RuntimeError(
            "No RealSense device connected. Check USB cable/port, close apps using the camera, "
            "then reconnect the device."
        )

    device = devices[0]
    try:
        name = device.get_info(rs.camera_info.name)
        serial = device.get_info(rs.camera_info.serial_number)
        print(f"RealSense Device: {name} (S/N: {serial})")
    except Exception:
        print("RealSense device detected.")

    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, DEPTH_WIDTH, DEPTH_HEIGHT, rs.format.z16, CAMERA_FPS)
    config.enable_stream(rs.stream.color, COLOR_WIDTH, COLOR_HEIGHT, rs.format.bgr8, CAMERA_FPS)
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
    global latest_filtered, lidar_running, scans_buffer
    try:
        for scan in lidar.iter_scans():
            if not lidar_running:
                break
            filtered = filter_scan(scan)
            with scan_lock:
                latest_filtered = list(filtered)        # tránh reference reuse
                scans_buffer.append(list(filtered))     # copy an toàn
                MAX_BUFFER = 50
                if len(scans_buffer) > MAX_BUFFER:
                    scans_buffer.pop(0)
            time.sleep(0.01)

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

        plt.pause(0.01)

        # keep polar alive
        now = time.time()
        if now - last_update >= PLOT_UPDATE_INTERVAL:
            update_polar(polar_ax, polar_line, polar_fig, count)
            last_update = now

    cv2.destroyWindow("Select Points")
    return clicked_points[0], clicked_points[1]

def map_lidar_to_image(bar_points, p1, p2):
    if p1[0] >= p2[0]:
        print("P1 phải nằm bên trái P2 — chọn lại!")
        return []
    
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
    """Show image with mapped lidar points, then accept or reject the sample."""
    result = color_img.copy()
    cv2.line(result, p1, p2, (255, 255, 0), 2)
    for pt in mapped_points:
        cv2.circle(result, (pt['pixel_x'], pt['pixel_y']), 3, (0, 255, 0), -1)

    cv2.rectangle(result, (0, 0), (COLOR_WIDTH, 58), (0, 0, 0), -1)
    cv2.putText(result, f"Mapped points: {len(mapped_points)} | Saved samples: {count}",
                (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    cv2.putText(result, "Enter/A: accept and save | R: reject sample",
                (10, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)

    cv2.namedWindow("Result")
    cv2.moveWindow("Result", 700, 50)
    cv2.imshow("Result", result)
    print("--- Result shown. Press Enter/A to save, R to reject ---")

    last_update = time.time()
    accepted = None
    while True:
        key = cv2.waitKey(30) & 0xFF
        if key == 13 or key == ord('a'):
            accepted = True
            break
        if key == ord('r'):
            accepted = False
            break
        plt.pause(0.01)
        
        now = time.time()
        if now - last_update >= PLOT_UPDATE_INTERVAL:
            update_polar(polar_ax, polar_line, polar_fig, count)
            last_update = now

    cv2.destroyWindow("Result")
    return result, accepted

def save_all(color_img, depth_img, result_img, calibration_data, timestamp):
    """Save images and calibration json"""
    color_dir = os.path.join(OUTPUT_DIR, "color")
    depth_dir = os.path.join(OUTPUT_DIR, "depth")
    depth_cm_dir = os.path.join(OUTPUT_DIR, "depth_colormap")
    calib_dir = os.path.join(OUTPUT_DIR, "pair")

    for d in [color_dir, depth_dir, depth_cm_dir, calib_dir]:
        os.makedirs(d, exist_ok=True)

    cv2.imwrite(os.path.join(color_dir, f"color_{timestamp}.png"), color_img)
    cv2.imwrite(os.path.join(depth_dir, f"depth_{timestamp}.png"), depth_img)

    depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_img, alpha=0.03), cv2.COLORMAP_JET)
    cv2.imwrite(os.path.join(depth_cm_dir, f"depth_colormap_{timestamp}.png"), depth_colormap)

    cv2.imwrite(os.path.join(calib_dir, f"pair_{timestamp}.png"), result_img)

    with open(os.path.join(calib_dir, f"pair_{timestamp}.json"), 'w') as f:
        json.dump(calibration_data, f, indent=2)

    print(f"  Saved to {OUTPUT_DIR}/ (timestamp: {timestamp})")

def calibrate(pipeline, align, scan_data, timestamp, polar_ax, polar_line, polar_fig, count):
    """Full calibration flow: denoise -> lidar select -> camera select -> map -> save"""

    # capture camera first to avoid timeout
    color_img, depth_img = capture_frames(pipeline, align)
    if color_img is None:
        print("Failed to capture camera frames!")
        return None

    # 0. Lọc nhiễu LiDAR
    print("\n--- Denoising LiDAR data ---")
    denoised = denoise_lidar_scans(num_scans=DENOISE_SCAN_COUNT)
    if len(denoised) == 0:
        print("  Denoising failed!")
        return None

    # 1. select bar on denoised polar plot
    print("\n--- Select bar points on Denoised LiDAR (Polar) ---")
    bar = select_bar_points_polar(denoised, polar_ax, polar_line, polar_fig, count)
    if bar is None or len(bar) < 2:
        print("  Cancelled or not enough points.")
        return None

    # 2. select P1 P2 on RGB
    p1, p2 = select_image_points(color_img, polar_ax, polar_line, polar_fig, count)
    if p1 is None:
        print("  Cancelled.")
        return None

    # 3. map lidar -> image
    mapped = map_lidar_to_image(bar, p1, p2)
    if len(mapped) == 0:
        print("  Mapping failed or no mapped points. Sample rejected.")
        return None

    angles = [a for _, a, _ in bar]
    dists = [d for _, _, d in bar]
    avg_distance = sum(dists) / len(dists)

    # Lưu thêm dữ liệu Cartesian
    cartesian_points = []
    for _, angle, dist in bar:
        x, z = polar_to_cartesian(angle, dist)
        cartesian_points.append({'angle': angle, 'distance': dist, 'x': x, 'z': z})

    calibration_data = {
        'timestamp': timestamp,
        'timestamp_iso': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp / 1000)),
        'source_script': 'collect_calibration.py',
        'hardware': {
            'lidar_model': 'RPLidar A1M8',
            'lidar_port': PORT,
            'camera_model': 'Intel RealSense D435'
        },
        'capture_config': {
            'color_width': COLOR_WIDTH,
            'color_height': COLOR_HEIGHT,
            'depth_width': DEPTH_WIDTH,
            'depth_height': DEPTH_HEIGHT,
            'fps': CAMERA_FPS,
            'front_angle_min_deg': FRONT_ANGLE_MIN,
            'front_angle_max_deg': FRONT_ANGLE_MAX
        },
        'image_point_start': p1,
        'image_point_end': p2,
        'lidar_angle_min': min(angles),
        'lidar_angle_max': max(angles),
        'lidar_points_count': len(bar),
        'mapped_points_count': len(mapped),
        'avg_distance': avg_distance,
        'denoising_method': 'multiple_scans_rounded_angles',
        'denoising_scans_count': DENOISE_SCAN_COUNT,
        'bar_distance_jump_threshold_mm': BAR_DISTANCE_JUMP_THRESHOLD_MM,
        'cartesian_points': cartesian_points,
        'mapped_points': mapped
    }

    print("  Sample summary:")
    print(f"    Bar points: {len(bar)}")
    print(f"    Mapped points: {len(mapped)}")
    print(f"    Angle range: {min(angles):.0f} to {max(angles):.0f} deg")
    print(f"    Average distance: {avg_distance:.1f} mm")

    # 4. show result
    result_img, accepted = show_result(color_img, mapped, p1, p2, polar_ax, polar_line, polar_fig, count)
    if not accepted:
        print("  Sample rejected by user.")
        return None

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

            if keyboard.is_pressed('s') and not save_request:
                save_request = True

    except KeyboardInterrupt:
        print("Interrupted.")
    finally:
        lidar_running = False

def cleanup(lidar=None, csv_file=None, pipeline=None, lidar_thread=None):
    global lidar_running
    lidar_running = False

    if lidar_thread is not None:
        lidar_thread.join(timeout=2)

    if csv_file is not None:
        try:
            csv_file.close()
        except:
            pass

    if lidar is not None:
        try:
            lidar.stop()
            lidar.disconnect()
        except:
            pass

    plt.close('all')
    cv2.destroyAllWindows()
    if pipeline is not None:
        try:
            pipeline.stop()
        except:
            pass

    print("Cleaned up.")

if __name__ == "__main__":
    lidar = None
    pipeline = None
    csv_file = None
    align = None
    writer = None
    try:
        lidar = init_lidar()
        pipeline, align = init_realsense()
        csv_file, writer = init_csv(CSV_FILE)
        main_loop(lidar, writer, pipeline, align)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Startup/runtime error: {e}")
    finally:
        cleanup(lidar=lidar, csv_file=csv_file, pipeline=pipeline)
