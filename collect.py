from rplidar import RPLidar
import math
import matplotlib.pyplot as plt
import time 
import csv
import keyboard # For keyboard input
import pyrealsense2 as rs
import numpy as np
import cv2
import os

PORT = "COM3"  # Update this to your RPLidar port
CSV_FILE = "lidar_data.csv"
PLOT_UPDATE_INTERVAL = 0.2  # seconds
OUTPUT_DIR = "captured_data"

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

    #config streams
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    # Start streaming
    profile = pipeline.start(config)

    align_to = rs.stream.color
    align = rs.align(align_to)
    
    return pipeline, align

def init_plot():
    plt.ion()
    fig, ax = plt.subplots(subplot_kw={'projection': 'polar'})
    ax.set_ylim(0, 6000)  # Set max distance (in mm)
    ax.set_title("RPLidar Real-Time Scan")
    line, = ax.plot([], [], 'b.', markersize=1)
    return fig, ax, line

def init_csv(file_name):
    f = open(file_name, mode='w', newline='')
    writer = csv.writer(f)
    writer.writerow(['Time', 'Angle', 'Distance'])
    return f, writer

def update_plot(ax, line, current_scan, save_count):
    if len(current_scan) == 0:
        return
    
    angles = []
    distances = []
    
    try:
        for _,angle, distance in current_scan:
            angles.append(math.radians(angle))
            distances.append(distance)
        
        line.set_data(angles, distances)
        ax.set_title(f'LiDAR - Saved: {save_count} times - Points: {len(current_scan)}')
        plt.pause(0.001)
    
    except Exception as e:
        print(f"Error updating plot: {e}")

def save_scan_data(writer, scan_data, timestamp):
    for _,angle, distance in scan_data:
        if distance > 0:  # Only save valid distances
            writer.writerow([
                timestamp, 
                round(angle, 2), 
                int(distance)
                ])

def capture_realsense_image(pipeline, align, timestamp):
    try:
        #wait frames
        frames = pipeline.wait_for_frames(timeout_ms=5000)

        # Align the depth frame to color frame
        aligned_frames = align.process(frames)

        # Get aligned frames
        depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()


        if not depth_frame or not color_frame:
            print("Warning: Could not acquire depth or color frames.")
            return False
        
        # Convert images to numpy arrays
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        # Create output directory if it doesn't exist
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
        
        # Create foldernames
        color_dir = os.path.join(OUTPUT_DIR, "color")
        depth_dir =  os.path.join(OUTPUT_DIR, "depth")
        depth_colormap_dir = os.path.join(OUTPUT_DIR, "depth_colormap")

        # Create directories if they don't exist
        os.makedirs(color_dir, exist_ok=True)
        os.makedirs(depth_dir, exist_ok=True)
        os.makedirs(depth_colormap_dir, exist_ok=True)

        # Creatre filenames
        rgb_filename = os.path.join(color_dir, f"color_{timestamp}.png")
        depth_filename = os.path.join(depth_dir, f"depth_{timestamp}.png")
        depth_colormap_filename = os.path.join(depth_colormap_dir, f"depth_colormap_{timestamp}.png")

        # Save color image
        cv2.imwrite(rgb_filename, color_image)

        # save depth image
        cv2.imwrite(depth_filename, depth_image)

        # Create and save depth colormap image
        depth_colormap = cv2.applyColorMap(
            cv2.convertScaleAbs(depth_image, alpha=0.03), 
            cv2.COLORMAP_JET
        )
        cv2.imwrite(depth_colormap_filename, depth_colormap)

        print(f"Saved RGB : {rgb_filename}")
        print(f"Saved Depth : {depth_filename}")
        print(f"Saved Depth Colormap : {depth_colormap_filename}")

        return True
    
    except Exception as e:
        print(f"Error capturing RealSense image: {e}")
        return False

def main_loop(lidar, writer, pipeline, align):
    print('Starting main loop. Press "s" to save')

    fig, ax, line = init_plot()
    save_count = 0
    save_request = False
    last_plot_time = time.time()

    for scan_data in lidar.iter_scans():
        current_time = time.time()
        if current_time - last_plot_time >= PLOT_UPDATE_INTERVAL:
            if plt.fignum_exists(fig.number):    
                update_plot(ax, line, scan_data, save_count)
            last_plot_time = current_time

        if save_request:
            timestamp = int(time.time() * 1000)
            print(f"\n ===Saving scan #{save_count + 1} (timestamp: {timestamp})===")

            save_scan_data(writer, scan_data, timestamp)
            capture_realsense_image(pipeline, align, timestamp)

            save_count += 1
            print(f"-> Saved scan #{save_count} with {len(scan_data)} points.")
            save_request = False

        if keyboard.is_pressed('s'):
            save_request = True

def cleanup(lidar, csv_file, pipeline):
    csv_file.close()
    lidar.stop()
    lidar.disconnect()
    plt.close()
    pipeline.stop()
    print("Stopped and disconnected LIDAR.")

if __name__ == "__main__":
    lidar = init_lidar()
    pipeline, align = init_realsense()
    csv_file, writer = init_csv(CSV_FILE)
    try:
        main_loop(lidar, writer, pipeline, align)
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        cleanup(lidar, csv_file, pipeline)



