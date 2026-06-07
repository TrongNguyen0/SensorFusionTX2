import argparse
import time

import cv2
import numpy as np
import pyrealsense2 as rs


def parse_args():
    parser = argparse.ArgumentParser(description="Minimal RealSense RGB + depth test")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=30)
    return parser.parse_args()


def main():
    args = parse_args()
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, args.width, args.height, rs.format.z16, args.fps)
    config.enable_stream(rs.stream.color, args.width, args.height, rs.format.bgr8, args.fps)

    print("Starting RealSense {}x{} @ {} FPS".format(args.width, args.height, args.fps))
    pipeline.start(config)
    align = rs.align(rs.stream.color)

    frame_count = 0
    last_time = time.time()
    fps = 0.0

    try:
        while True:
            frames = pipeline.wait_for_frames()
            aligned = align.process(frames)
            depth_frame = aligned.get_depth_frame()
            color_frame = aligned.get_color_frame()

            if not depth_frame or not color_frame:
                continue

            color = np.asanyarray(color_frame.get_data())
            depth = np.asanyarray(depth_frame.get_data())
            depth_vis = cv2.applyColorMap(
                cv2.convertScaleAbs(depth, alpha=0.03),
                cv2.COLORMAP_JET,
            )

            now = time.time()
            dt = max(now - last_time, 1e-6)
            last_time = now
            instant_fps = 1.0 / dt
            fps = instant_fps if fps == 0.0 else 0.9 * fps + 0.1 * instant_fps
            frame_count += 1

            cv2.putText(
                color,
                "FPS: {:.1f} | Frame: {}".format(fps, frame_count),
                (15, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

            display = np.vstack((color, depth_vis))
            cv2.imshow("RealSense RGB + Depth", display)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break

    finally:
        pipeline.stop()
        cv2.destroyAllWindows()
        print("RealSense stopped.")


if __name__ == "__main__":
    main()
