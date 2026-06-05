from typing import Optional

import cv2
import numpy as np


class FusionVisualizer(object):
    def __init__(
        self,
        point_radius: int = 3,
        point_color=(0, 255, 0),
        depth_alpha: float = 0.03,
    ) -> None:
        self.point_radius = point_radius
        self.point_color = point_color
        self.depth_alpha = depth_alpha

    def create_frame(
        self,
        color_image: np.ndarray,
        depth_image: np.ndarray,
        image_points: np.ndarray,
        frame_id: int,
        fps: float,
    ) -> np.ndarray:
        fusion = color_image.copy()
        self._draw_points(fusion, image_points)
        self._draw_overlay(fusion, frame_id, fps, len(image_points))

        depth_vis = self.depth_to_colormap(depth_image)
        if depth_vis.shape[:2] != fusion.shape[:2]:
            depth_vis = cv2.resize(depth_vis, (fusion.shape[1], fusion.shape[0]))

        return np.vstack((fusion, depth_vis))

    def depth_to_colormap(self, depth_image: np.ndarray) -> np.ndarray:
        depth_scaled = cv2.convertScaleAbs(depth_image, alpha=self.depth_alpha)
        return cv2.applyColorMap(depth_scaled, cv2.COLORMAP_JET)

    def _draw_points(self, image: np.ndarray, image_points: np.ndarray) -> None:
        if image_points is None or len(image_points) == 0:
            return

        for point in image_points:
            u, v = int(point[0]), int(point[1])
            cv2.circle(image, (u, v), self.point_radius, self.point_color, -1)

    @staticmethod
    def _draw_overlay(image: np.ndarray, frame_id: int, fps: float, point_count: int) -> None:
        text = "Frame: {} | FPS: {:.1f} | LiDAR points: {}".format(
            frame_id, fps, point_count
        )
        cv2.rectangle(image, (8, 8), (520, 42), (0, 0, 0), -1)
        cv2.putText(
            image,
            text,
            (16, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
