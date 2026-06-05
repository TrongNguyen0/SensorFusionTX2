import json
import os
import time
from typing import Any, Dict, Sequence

import cv2
import numpy as np


class DatasetLogger(object):
    def __init__(self, root_dir: str = "dataset") -> None:
        self.root_dir = root_dir
        os.makedirs(self.root_dir, exist_ok=True)

    def save(
        self,
        color_image: np.ndarray,
        depth_image: np.ndarray,
        fusion_image: np.ndarray,
        lidar_points: Sequence[object],
        frame_id: int,
        metadata: Dict[str, Any] = None,
    ) -> str:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        folder = os.path.join(self.root_dir, timestamp)
        suffix = 1
        while os.path.exists(folder):
            folder = os.path.join(self.root_dir, "{}_{:02d}".format(timestamp, suffix))
            suffix += 1
        os.makedirs(folder)

        cv2.imwrite(os.path.join(folder, "color.png"), color_image)
        cv2.imwrite(os.path.join(folder, "depth.png"), depth_image)
        cv2.imwrite(os.path.join(folder, "fusion.png"), fusion_image)

        lidar_array = self._lidar_to_array(lidar_points)
        np.save(os.path.join(folder, "lidar.npy"), lidar_array)

        info = {
            "timestamp": timestamp,
            "frame_id": frame_id,
            "number_of_points": int(len(lidar_array)),
        }
        if metadata:
            info.update(metadata)

        with open(os.path.join(folder, "metadata.json"), "w") as f:
            json.dump(info, f, indent=2, sort_keys=True)

        return folder

    @staticmethod
    def _lidar_to_array(lidar_points: Sequence[object]) -> np.ndarray:
        rows = []
        for point in lidar_points:
            angle = DatasetLogger._get_value(point, "angle", None)
            distance = DatasetLogger._get_value(point, "distance", None)
            quality = DatasetLogger._get_value(point, "quality", 0)
            if angle is None or distance is None:
                continue
            rows.append((float(angle), float(distance), float(quality)))

        if not rows:
            return np.empty((0, 3), dtype=np.float32)
        return np.asarray(rows, dtype=np.float32)

    @staticmethod
    def _get_value(obj, name: str, default):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
