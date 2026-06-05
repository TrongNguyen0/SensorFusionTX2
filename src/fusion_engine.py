from typing import Iterable, List, NamedTuple, Optional, Sequence, Tuple

import numpy as np


class FusionResult(NamedTuple):
    image_points: np.ndarray
    camera_points: np.ndarray
    lidar_points: np.ndarray


class FusionEngine(object):
    def __init__(
        self,
        K: np.ndarray,
        R: np.ndarray,
        T: np.ndarray,
        image_width: int,
        image_height: int,
        min_distance_mm: float = 50.0,
        max_distance_mm: float = 12000.0,
        min_camera_z_mm: float = 1.0,
    ) -> None:
        self.K = np.asarray(K, dtype=np.float64)
        self.R = np.asarray(R, dtype=np.float64)
        self.T = np.asarray(T, dtype=np.float64).reshape(3, 1)
        self.image_width = image_width
        self.image_height = image_height
        self.min_distance_mm = min_distance_mm
        self.max_distance_mm = max_distance_mm
        self.min_camera_z_mm = min_camera_z_mm

    def project_lidar(self, lidar_scan: Sequence[object]) -> FusionResult:
        lidar_xyz = self._lidar_scan_to_xyz(lidar_scan)
        if lidar_xyz.size == 0:
            return FusionResult(
                image_points=np.empty((0, 2), dtype=np.int32),
                camera_points=np.empty((0, 3), dtype=np.float64),
                lidar_points=np.empty((0, 3), dtype=np.float64),
            )

        camera_xyz = self._transform_to_camera(lidar_xyz)
        image_points, camera_points, lidar_points = self._project(camera_xyz, lidar_xyz)
        return FusionResult(
            image_points=image_points,
            camera_points=camera_points,
            lidar_points=lidar_points,
        )

    def _lidar_scan_to_xyz(self, lidar_scan: Sequence[object]) -> np.ndarray:
        xyz = []
        for point in lidar_scan:
            angle = self._get_value(point, "angle", None)
            distance = self._get_value(point, "distance", None)
            if angle is None or distance is None:
                continue

            try:
                angle_f = float(angle)
                distance_f = float(distance)
            except (TypeError, ValueError):
                continue

            if distance_f <= self.min_distance_mm or distance_f >= self.max_distance_mm:
                continue

            angle_rad = np.deg2rad(angle_f)
            x = distance_f * np.sin(angle_rad)
            y = 0.0
            z = distance_f * np.cos(angle_rad)
            xyz.append((x, y, z))

        if not xyz:
            return np.empty((0, 3), dtype=np.float64)
        return np.asarray(xyz, dtype=np.float64)

    def _transform_to_camera(self, lidar_xyz: np.ndarray) -> np.ndarray:
        return (self.R.dot(lidar_xyz.T) + self.T).T

    def _project(
        self, camera_xyz: np.ndarray, lidar_xyz: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        z = camera_xyz[:, 2]
        valid_z = z > self.min_camera_z_mm
        camera_xyz = camera_xyz[valid_z]
        lidar_xyz = lidar_xyz[valid_z]

        if camera_xyz.size == 0:
            return (
                np.empty((0, 2), dtype=np.int32),
                np.empty((0, 3), dtype=np.float64),
                np.empty((0, 3), dtype=np.float64),
            )

        uvw = self.K.dot(camera_xyz.T).T
        u = uvw[:, 0] / uvw[:, 2]
        v = uvw[:, 1] / uvw[:, 2]

        in_image = (
            (u >= 0)
            & (u < self.image_width)
            & (v >= 0)
            & (v < self.image_height)
            & np.isfinite(u)
            & np.isfinite(v)
        )

        image_points = np.stack((u[in_image], v[in_image]), axis=1).astype(np.int32)
        camera_points = camera_xyz[in_image]
        lidar_points = lidar_xyz[in_image]
        return image_points, camera_points, lidar_points

    @staticmethod
    def _get_value(obj, name: str, default):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
