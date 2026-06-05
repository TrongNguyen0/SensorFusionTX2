import logging
import os
from typing import Tuple

import numpy as np


class CalibrationData(object):
    def __init__(self, K: np.ndarray, R: np.ndarray, T: np.ndarray) -> None:
        self.K = K
        self.R = R
        self.T = T


class CalibrationLoader(object):
    def __init__(self, path: str) -> None:
        self.path = path
        self.logger = logging.getLogger(self.__class__.__name__)

    def load(self) -> CalibrationData:
        if not os.path.exists(self.path):
            raise FileNotFoundError("Calibration file not found: {}".format(self.path))

        self.logger.info("Loading calibration from %s", self.path)
        data = np.load(self.path)

        for key in ("K", "R", "T"):
            if key not in data:
                raise ValueError("Calibration file missing key '{}'".format(key))

        K = self._as_float64(data["K"], "K")
        R = self._as_float64(data["R"], "R")
        T = self._as_float64(data["T"], "T")

        if K.shape != (3, 3):
            raise ValueError("K must have shape (3, 3), got {}".format(K.shape))
        if R.shape != (3, 3):
            raise ValueError("R must have shape (3, 3), got {}".format(R.shape))
        if T.shape == (3,):
            T = T.reshape(3, 1)
        if T.shape != (3, 1):
            raise ValueError("T must have shape (3, 1) or (3,), got {}".format(T.shape))

        self._validate_finite(K, "K")
        self._validate_finite(R, "R")
        self._validate_finite(T, "T")
        self._validate_camera_matrix(K)

        self.logger.info("Calibration loaded: K%s R%s T%s", K.shape, R.shape, T.shape)
        return CalibrationData(K=K, R=R, T=T)

    @staticmethod
    def load_matrices(path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        calibration = CalibrationLoader(path).load()
        return calibration.K, calibration.R, calibration.T

    @staticmethod
    def _as_float64(array: np.ndarray, name: str) -> np.ndarray:
        if not isinstance(array, np.ndarray):
            raise TypeError("{} must be a numpy array".format(name))
        return np.asarray(array, dtype=np.float64)

    @staticmethod
    def _validate_finite(array: np.ndarray, name: str) -> None:
        if not np.all(np.isfinite(array)):
            raise ValueError("{} contains NaN or inf values".format(name))

    @staticmethod
    def _validate_camera_matrix(K: np.ndarray) -> None:
        if K[0, 0] <= 0 or K[1, 1] <= 0:
            raise ValueError("Camera focal length in K must be positive")
        if abs(K[2, 2]) < 1e-12:
            raise ValueError("K[2, 2] must be non-zero")
