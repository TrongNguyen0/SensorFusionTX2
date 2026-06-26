import os
import json
import re
import sys
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np
from PyQt5.QtCore import QPoint, QProcess, QProcessEnvironment, QSize, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QHeaderView,
    QMainWindow,
    QPushButton,
    QPlainTextEdit,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import pyrealsense2 as rs
from rplidar import RPLidar

from core.collect_core import (
    REQUIRED_CALIBRATION_POINTS,
    build_calibration_data,
    build_correspondences,
    render_pair_preview,
    save_sample,
)
from core.fusion_core import (
    load_calibration,
    metrics_to_text,
    process_scan,
    render_dense_depth,
    save_fusion_frame,
)
from core.lidar_core import (
    DISPLAY_SMOOTH_ANGLE_BIN_DEG,
    DISPLAY_SMOOTH_SCAN_COUNT,
    denoise_scans,
    extract_corner_features,
    filter_scan,
    polar_to_cartesian,
    smooth_scan_for_display,
)


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "captured_data")
FUSION_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "fusion_output")
CALIB_FILE = os.path.join(PROJECT_ROOT, "calibration_result_pnp.npz")
CALIB_METRICS_FILE = os.path.join(PROJECT_ROOT, "data", "calibration_result", "calibration_metrics.json")
LIDAR_PORT = "COM3"
COLOR_WIDTH = 640
COLOR_HEIGHT = 480
DEPTH_WIDTH = 640
DEPTH_HEIGHT = 480
CAMERA_FPS = 30
LIDAR_DISPLAY_RANGE_MM = 4000
LIDAR_GRID_STEP_MM = 1000
FUSION_DENOISE_SCAN_COUNT = 5
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp"}
TEXT_EXTS = {".json", ".txt", ".md"}

APP_STYLE = """
QMainWindow, QWidget {
    background: #f3f8fc;
    color: #18212f;
    font-family: Segoe UI;
    font-size: 10pt;
}
QWidget#controlPanel {
    background: #f8fbff;
    border-left: 1px solid #d8e7f5;
}
QLabel {
    background: transparent;
}
QGroupBox {
    background: #ffffff;
    border: 1px solid #cfe0ee;
    border-radius: 6px;
    margin-top: 10px;
    padding: 12px 8px 8px 8px;
    font-weight: 700;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QPushButton {
    min-height: 34px;
    border: 1px solid #93c5fd;
    border-radius: 6px;
    background: #e0f2fe;
    color: #0f3f66;
    padding: 6px 10px;
    font-weight: 700;
}
QPushButton:hover {
    background: #dbeafe;
    border-color: #60a5fa;
}
QPushButton:pressed {
    background: #bfdbfe;
    border-color: #3b82f6;
}
QPushButton:disabled {
    color: #94a3b8;
    background: #eef2f6;
    border-color: #d8e0ea;
}
QPushButton#primaryButton,
QPushButton#successButton,
QPushButton#dangerButton,
QPushButton#secondaryButton,
QPushButton#categoryButton {
    color: #0f3f66;
    background: #e0f2fe;
    border-color: #93c5fd;
}
QPushButton#primaryButton:hover,
QPushButton#successButton:hover,
QPushButton#dangerButton:hover,
QPushButton#secondaryButton:hover,
QPushButton#categoryButton:hover {
    color: #0b3b63;
    background: #dbeafe;
    border-color: #60a5fa;
}
QPushButton#primaryButton:pressed,
QPushButton#successButton:pressed,
QPushButton#dangerButton:pressed,
QPushButton#secondaryButton:pressed,
QPushButton#categoryButton:pressed {
    background: #bfdbfe;
    border-color: #3b82f6;
}
QPushButton#categoryButton {
    min-height: 34px;
    font-weight: 700;
}
QComboBox, QListWidget, QPlainTextEdit, QTableWidget {
    border: 1px solid #cfe0ee;
    border-radius: 4px;
    background: #ffffff;
}
QTableWidget {
    gridline-color: #e2e8f0;
    selection-background-color: #dbeafe;
    selection-color: #0f172a;
}
QHeaderView::section {
    color: #ffffff;
    background: #153a66;
    border: 0;
    border-right: 1px solid #315b89;
    padding: 8px 10px;
    font-weight: 700;
}
QLabel#computeTitle {
    color: #0f172a;
    font-size: 26px;
    font-weight: 800;
}
QLabel#computeSubtitle {
    color: #64748b;
    font-size: 12pt;
}
QLabel#computeSectionTitle {
    color: #18212f;
    font-size: 15pt;
    font-weight: 800;
}
QFrame#metricCard, QFrame#matrixCard {
    background: #ffffff;
    border: 1px solid #d7e0ea;
    border-radius: 7px;
}
QLabel#metricTitle {
    color: #526174;
    font-size: 10.5pt;
    font-weight: 700;
}
QLabel#metricValue {
    color: #0f172a;
    font-size: 24pt;
    font-weight: 800;
}
QLabel#metricHint {
    color: #64748b;
}
QLabel#matrixTitle {
    color: #172033;
    font-size: 12pt;
    font-weight: 800;
}
QLabel#matrixValue {
    color: #0f172a;
    font-family: Consolas;
    font-size: 10.5pt;
}
QLabel#matrixHint {
    color: #64748b;
}
QLabel#computeStatusPill {
    color: #ffffff;
    background: #64748b;
    border-radius: 14px;
    padding: 6px 14px;
    font-weight: 800;
}
QComboBox {
    min-height: 34px;
    padding: 5px 10px;
    font-weight: 700;
    color: #0f3f66;
    background: #e0f2fe;
    border: 1px solid #93c5fd;
    border-radius: 6px;
}
QComboBox:hover {
    background: #dbeafe;
    border-color: #60a5fa;
}
QComboBox::drop-down {
    width: 30px;
    border-left: 1px solid #93c5fd;
}
QComboBox QAbstractItemView {
    color: #0f3f66;
    background: #ffffff;
    selection-background-color: #dbeafe;
    selection-color: #0b3b63;
    padding: 6px;
    outline: 0;
}
QComboBox QAbstractItemView::item {
    min-height: 30px;
    padding: 6px 10px;
}
QListWidget {
    padding: 6px;
    outline: 0;
}
QListWidget::item {
    min-height: 30px;
    padding: 6px 10px;
    margin: 3px 0;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    background: #f8fafc;
}
QListWidget::item:hover {
    background: #eef6ff;
    border-color: #7db3ed;
}
QListWidget::item:selected {
    color: #ffffff;
    background: #2563eb;
    border-color: #1d4ed8;
}
QLabel#sectionLabel {
    color: #0f172a;
    font-weight: 700;
    margin-top: 6px;
}
QLabel#pathLabel {
    color: #475569;
    font-weight: 600;
}
QLabel#statusLabel {
    color: #0f172a;
    font-weight: 700;
}
QLabel#imageView {
    background: #101820;
    color: #d7dee8;
    border: 1px solid #c4ccd6;
    border-radius: 4px;
}
QFrame#sourceFrame {
    background: #ffffff;
    border: 1px solid #b9c4d0;
    border-radius: 5px;
}
"""


def bgr_to_qpixmap(image_bgr):
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    height, width, channels = image_rgb.shape
    bytes_per_line = channels * width
    qimage = QImage(image_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
    return QPixmap.fromImage(qimage.copy())


def imread_unicode(path):
    if not os.path.exists(path):
        return None
    data = np.fromfile(path, dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_UNCHANGED)


def prepare_image_for_display(image):
    if image is None:
        return None
    if image.ndim == 2:
        if image.dtype == np.uint16:
            image_8u = cv2.convertScaleAbs(image, alpha=0.03)
        else:
            image_8u = cv2.convertScaleAbs(image)
        return cv2.cvtColor(image_8u, cv2.COLOR_GRAY2BGR)
    if image.ndim == 3 and image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image


def section_label(text):
    label = QLabel(text)
    label.setObjectName("sectionLabel")
    return label


def set_button_kind(button, kind):
    object_names = {
        "primary": "primaryButton",
        "success": "successButton",
        "danger": "dangerButton",
        "secondary": "secondaryButton",
    }
    button.setObjectName(object_names.get(kind, "secondaryButton"))
    return button


class ImageView(QLabel):
    point_clicked = pyqtSignal(int, int)

    def __init__(self, title):
        super().__init__(title)
        self.setObjectName("imageView")
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(640, 320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFrameShape(QFrame.StyledPanel)
        self._pixmap = None
        self._image_size = None
        self._scaled_size = None

    def set_image(self, image_bgr):
        self._image_size = (image_bgr.shape[1], image_bgr.shape[0])
        self._pixmap = bgr_to_qpixmap(image_bgr)
        self._update_scaled_pixmap()

    def clear_image(self, text):
        self._pixmap = None
        self._image_size = None
        self._scaled_size = None
        self.clear()
        self.setText(text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_scaled_pixmap()

    def mousePressEvent(self, event):
        if self._image_size is None or self._scaled_size is None:
            return

        label_w = self.width()
        label_h = self.height()
        pix_w, pix_h = self._scaled_size
        offset_x = (label_w - pix_w) / 2
        offset_y = (label_h - pix_h) / 2

        x = event.pos().x() - offset_x
        y = event.pos().y() - offset_y
        if not (0 <= x < pix_w and 0 <= y < pix_h):
            return

        image_w, image_h = self._image_size
        image_x = int(x * image_w / pix_w)
        image_y = int(y * image_h / pix_h)
        self.point_clicked.emit(image_x, image_y)

    def _update_scaled_pixmap(self):
        if self._pixmap is None:
            return
        scaled = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._scaled_size = (scaled.width(), scaled.height())
        self.setPixmap(scaled)


class LidarPlotWidget(QWidget):
    point_clicked = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(640, 320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.points = []
        self.manual_clicks = []
        self.feature_points = []
        self.feature_lines = []
        self.support_points = []
        self.inlier_points = []
        self.display_range = float(LIDAR_DISPLAY_RANGE_MM)
        self.debug_metrics = {}

    def set_points(self, points, debug_metrics=None):
        self.points = list(points)
        self.debug_metrics = debug_metrics or {}
        self.update()

    def set_selected(self, points):
        self.feature_points = list(points)
        self.update()

    def set_manual_clicks(self, clicks):
        self.manual_clicks = list(clicks)
        self.update()

    def set_feature_overlay(self, features=None, lines=None, support_points=None, inlier_points=None):
        self.feature_points = list(features or [])
        self.feature_lines = [line for line in (lines or []) if line]
        self.support_points = list(support_points or [])
        self.inlier_points = list(inlier_points or [])
        self.update()

    def mousePressEvent(self, event):
        x_mm, z_mm = self._screen_to_world(event.pos())
        self.point_clicked.emit({"x_mm": float(x_mm), "z_mm": float(z_mm)})

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(30, 30, 30))
        painter.setRenderHint(QPainter.Antialiasing)

        self._draw_grid(painter)
        self._draw_points(painter)
        self._draw_support_points(painter)
        self._draw_inlier_points(painter)
        self._draw_feature_lines(painter)
        self._draw_manual_clicks(painter)
        self._draw_selected(painter)
        self._draw_legend(painter)

        painter.setPen(QPen(QColor(230, 230, 230), 1))
        source = self.debug_metrics.get("source", "latest display scan")
        header = (
            f"LiDAR Plot ({source}) | points: {len(self.points)} | "
            f"range: {int(self.display_range / 1000)}m"
        )
        painter.drawText(12, 22, header)

    def _draw_grid(self, painter):
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        r = LIDAR_GRID_STEP_MM
        while r <= self.display_range:
            left = self._world_to_screen(-r, r)
            right = self._world_to_screen(r, -r)
            width = right.x() - left.x()
            height = right.y() - left.y()
            painter.drawArc(left.x(), left.y(), width, height, 0, 180 * 16)
            label = self._world_to_screen(0, r)
            painter.drawText(label.x() + 8, label.y() + 4, f"{r // 1000}m")
            r += LIDAR_GRID_STEP_MM

        painter.setPen(QPen(QColor(120, 120, 120), 1))
        origin = self._world_to_screen(0, 0)
        painter.drawLine(origin.x(), origin.y(), origin.x(), 20)
        painter.drawLine(0, origin.y(), self.width(), origin.y())

    def _draw_points(self, painter):
        painter.setPen(QPen(QColor(0, 240, 130), 1))
        painter.setBrush(QColor(0, 240, 130))
        for _, angle, distance in self.points:
            x, z = polar_to_cartesian(angle, distance)
            point = self._world_to_screen(x, z)
            painter.drawPoint(point)

    def _draw_support_points(self, painter):
        painter.setPen(QPen(QColor(255, 150, 40), 1))
        painter.setBrush(QColor(255, 150, 40))
        for item in self.support_points:
            point = self._world_to_screen(item["x_mm"], item["z_mm"])
            painter.drawEllipse(point, 1, 1)

    def _draw_inlier_points(self, painter):
        painter.setPen(QPen(QColor(0, 220, 255), 1))
        painter.setBrush(QColor(0, 220, 255))
        for item in self.inlier_points:
            point = self._world_to_screen(item["x_mm"], item["z_mm"])
            painter.drawEllipse(point, 2, 2)

    def _draw_feature_lines(self, painter):
        painter.setPen(QPen(QColor(80, 150, 255), 2))
        for line in self.feature_lines:
            start = line.get("start")
            end = line.get("end")
            if not start or not end:
                continue
            p1 = self._world_to_screen(start["x_mm"], start["z_mm"])
            p2 = self._world_to_screen(end["x_mm"], end["z_mm"])
            painter.drawLine(p1, p2)

    def _draw_manual_clicks(self, painter):
        painter.setPen(QPen(QColor(0, 220, 255), 2))
        painter.setBrush(QColor(0, 220, 255))
        for idx, click in enumerate(self.manual_clicks):
            point = self._world_to_screen(click["x_mm"], click["z_mm"])
            painter.drawEllipse(point, 5, 5)
            painter.drawText(point.x() + 8, point.y() + 14, f"C{idx + 1}")

    def _draw_selected(self, painter):
        painter.setPen(QPen(QColor(255, 60, 60), 2))
        painter.setBrush(QColor(255, 60, 60))
        for idx, item in enumerate(self.feature_points):
            point = self._world_to_screen(item["x_mm"], item["z_mm"])
            painter.drawEllipse(point, 5, 5)
            painter.drawText(point.x() + 8, point.y() - 8, f"P{idx + 1}")

    def _draw_legend(self, painter):
        x = self.width() - 230
        y = 12
        width = 216
        height = 82
        painter.setPen(QPen(QColor(70, 70, 70), 1))
        painter.setBrush(QColor(245, 245, 245, 230))
        painter.drawRect(x, y, width, height)

        items = [
            ("Laser data points", QColor(0, 240, 130), "point"),
            ("Selected points", QColor(0, 220, 255), "circle"),
            ("Selected virtual points", QColor(255, 60, 60), "circle"),
            ("Fitted line", QColor(80, 150, 255), "line"),
        ]
        text_x = x + 32
        item_y = y + 18
        for label, color, kind in items:
            marker_x = x + 16
            painter.setPen(QPen(color, 2))
            painter.setBrush(color)
            if kind == "line":
                painter.drawLine(marker_x - 6, item_y - 3, marker_x + 8, item_y - 3)
            elif kind == "point":
                painter.drawPoint(marker_x, item_y - 3)
            else:
                painter.drawEllipse(QPoint(marker_x, item_y - 3), 3, 3)
            painter.setPen(QPen(QColor(20, 20, 20), 1))
            painter.drawText(text_x, item_y + 1, label)
            item_y += 18

    def _world_to_screen(self, x_mm, z_mm):
        margin = 24
        usable_w = max(1, self.width() - 2 * margin)
        usable_h = max(1, self.height() - 2 * margin)
        x_norm = (x_mm + self.display_range) / (2 * self.display_range)
        z_norm = z_mm / self.display_range
        sx = margin + x_norm * usable_w
        sy = self.height() - margin - z_norm * usable_h
        return QPoint(int(sx), int(sy))

    def _screen_to_world(self, point):
        margin = 24
        usable_w = max(1, self.width() - 2 * margin)
        usable_h = max(1, self.height() - 2 * margin)
        x_norm = (point.x() - margin) / usable_w
        z_norm = (self.height() - margin - point.y()) / usable_h
        x_mm = x_norm * 2 * self.display_range - self.display_range
        z_mm = z_norm * self.display_range
        return x_mm, z_mm

class CameraWorker(QThread):
    frame_ready = pyqtSignal(object, object)
    status = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = False
        self.pipeline = None
        self.align = None

    def run(self):
        self.running = True
        try:
            ctx = rs.context()
            if len(ctx.query_devices()) == 0:
                self.status.emit("RealSense not connected")
                return

            self.pipeline = rs.pipeline()
            config = rs.config()
            config.enable_stream(rs.stream.depth, DEPTH_WIDTH, DEPTH_HEIGHT, rs.format.z16, CAMERA_FPS)
            config.enable_stream(rs.stream.color, COLOR_WIDTH, COLOR_HEIGHT, rs.format.bgr8, CAMERA_FPS)
            self.pipeline.start(config)
            self.align = rs.align(rs.stream.color)
            self.status.emit("Camera started")

            while self.running:
                frames = self.pipeline.wait_for_frames(timeout_ms=1000)
                aligned = self.align.process(frames)
                depth_frame = aligned.get_depth_frame()
                color_frame = aligned.get_color_frame()
                if not depth_frame or not color_frame:
                    continue
                color_img = np.asanyarray(color_frame.get_data()).copy()
                depth_img = np.asanyarray(depth_frame.get_data()).copy()
                self.frame_ready.emit(color_img, depth_img)
        except Exception as exc:
            self.status.emit(f"Camera error: {exc}")
        finally:
            if self.pipeline is not None:
                try:
                    self.pipeline.stop()
                except Exception:
                    pass
            self.status.emit("Camera stopped")

    def stop(self):
        self.running = False
        self.wait(2000)


class LidarWorker(QThread):
    scan_ready = pyqtSignal(object, object, int, object)
    status = pyqtSignal(str)

    def __init__(self, port):
        super().__init__()
        self.port = port
        self.running = False
        self.lidar = None

    def run(self):
        self.running = True
        display_buffer = deque(maxlen=DISPLAY_SMOOTH_SCAN_COUNT)
        try:
            self.lidar = RPLidar(self.port, baudrate=115200, timeout=3)
            self.status.emit(f"LiDAR started on {self.port}")
            for scan in self.lidar.iter_scans():
                if not self.running:
                    break
                filtered_scan = filter_scan(scan)
                display_buffer.append(filtered_scan)
                display_scan = smooth_scan_for_display(
                    list(display_buffer),
                    num_scans=DISPLAY_SMOOTH_SCAN_COUNT,
                    angle_bin_deg=DISPLAY_SMOOTH_ANGLE_BIN_DEG,
                )
                debug = {
                    "source": "display smoothed scan",
                    "raw_points": int(len(scan)),
                    "filtered_points": int(len(filtered_scan)),
                    "display_points": int(len(display_scan)),
                    "smooth_scans": int(min(len(display_buffer), DISPLAY_SMOOTH_SCAN_COUNT)),
                    "smooth_angle_bin_deg": float(DISPLAY_SMOOTH_ANGLE_BIN_DEG),
                }
                self.scan_ready.emit(filtered_scan, display_scan, len(scan), debug)
        except Exception as exc:
            self.status.emit(f"LiDAR error: {exc}")
        finally:
            if self.lidar is not None:
                try:
                    self.lidar.stop()
                    self.lidar.disconnect()
                except Exception:
                    pass
            self.status.emit("LiDAR stopped")

    def stop(self):
        self.running = False
        self.wait(3000)

class FusionWorker(QThread):
    frame_ready = pyqtSignal(object, object, object, object, object, object)
    status = pyqtSignal(str)

    def __init__(self, port, calib_file):
        super().__init__()
        self.port = port
        self.calib_file = calib_file
        self.running = False
        self.lidar = None
        self.pipeline = None

    def run(self):
        self.running = True
        try:
            K, dist_coeffs, R, T, rvec, tvec = load_calibration(self.calib_file)
            self.status.emit("Fusion calibration loaded")

            ctx = rs.context()
            if len(ctx.query_devices()) == 0:
                self.status.emit("RealSense not connected")
                return

            self.pipeline = rs.pipeline()
            config = rs.config()
            config.enable_stream(rs.stream.depth, DEPTH_WIDTH, DEPTH_HEIGHT, rs.format.z16, CAMERA_FPS)
            config.enable_stream(rs.stream.color, COLOR_WIDTH, COLOR_HEIGHT, rs.format.bgr8, CAMERA_FPS)
            profile = self.pipeline.start(config)
            depth_sensor = profile.get_device().first_depth_sensor()
            depth_scale = depth_sensor.get_depth_scale()
            align = rs.align(rs.stream.color)

            self.lidar = RPLidar(self.port, baudrate=115200, timeout=3)
            self.status.emit("Fusion sensors started")
            scan_buffer = deque(maxlen=FUSION_DENOISE_SCAN_COUNT)

            for scan in self.lidar.iter_scans():
                if not self.running:
                    break

                filtered_scan = filter_scan(scan)
                scan_buffer.append(filtered_scan)
                stable_scan = denoise_scans(list(scan_buffer), num_scans=FUSION_DENOISE_SCAN_COUNT)
                if not stable_scan:
                    continue

                frames = self.pipeline.wait_for_frames(timeout_ms=1000)
                aligned = align.process(frames)
                depth_frame = aligned.get_depth_frame()
                color_frame = aligned.get_color_frame()
                if not depth_frame or not color_frame:
                    continue

                color_img = np.asanyarray(color_frame.get_data()).copy()
                depth_img = np.asanyarray(depth_frame.get_data()).copy()
                overlay, sparse_depth, metrics = process_scan(
                    stable_scan, color_img, depth_img, depth_scale, K, dist_coeffs, R, T, rvec, tvec
                )
                metrics["raw_scan_points"] = int(len(scan))
                metrics["filtered_scan_points"] = int(len(filtered_scan))
                metrics["fusion_denoise_scans"] = int(min(len(scan_buffer), FUSION_DENOISE_SCAN_COUNT))
                dense_cm = render_dense_depth(depth_img)
                self.frame_ready.emit(color_img, depth_img, overlay, sparse_depth, dense_cm, metrics)

        except Exception as exc:
            self.status.emit(f"Fusion error: {exc}")
        finally:
            if self.lidar is not None:
                try:
                    self.lidar.stop()
                    self.lidar.disconnect()
                except Exception:
                    pass
            if self.pipeline is not None:
                try:
                    self.pipeline.stop()
                except Exception:
                    pass
            self.status.emit("Fusion stopped")

    def stop(self):
        self.running = False
        self.wait(3000)


class SensorFusionUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SensorFusion Calibration UI")
        self.resize(1300, 820)
        self.setStyleSheet(APP_STYLE)

        self.camera_worker = None
        self.lidar_worker = None
        self.fusion_worker = None
        self.process = None
        self.process_script_name = None

        self.latest_color = None
        self.latest_depth = None
        self.latest_scan = []
        self.latest_display_scan = []
        self.latest_lidar_debug = {}
        self.latest_raw_scan_count = 0

        self.snapshot_color = None
        self.snapshot_depth = None
        self.snapshot_lidar = []
        self.lidar_raw_clicks = []
        self.lidar_selected = []
        self.lidar_feature_extraction = None
        self.image_selected = []
        self.correspondences = []
        self.preview_img = None
        self.sample_count = 0
        self.state = "IDLE"
        self.latest_fusion_color = None
        self.latest_fusion_depth = None
        self.latest_fusion_overlay = None
        self.latest_fusion_sparse = None
        self.latest_fusion_metrics = None
        self.data_files = []
        self.data_index = 0
        self.data_current_key = None
        self.data_group_dir = None
        self.data_browser_level = "root"

        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)

        self.display_stack = QStackedWidget()
        self.display_stack.addWidget(self._build_collect_display())
        self.display_stack.addWidget(self._build_compute_display())
        self.display_stack.addWidget(self._build_fusion_display())
        self.display_stack.addWidget(self._build_data_display())

        control_panel = self._build_control_panel()
        root_layout.addWidget(self.display_stack, 3)
        root_layout.addWidget(control_panel, 1)
        self.setCentralWidget(root)

    def _build_collect_display(self):
        page = QWidget()
        layout = QGridLayout(page)
        self.camera_view = ImageView("Camera stream")
        self.lidar_view = LidarPlotWidget()
        self.camera_view.point_clicked.connect(self.on_image_clicked)
        self.lidar_view.point_clicked.connect(self.on_lidar_clicked)
        layout.addWidget(self.camera_view, 0, 0)
        layout.addWidget(self.lidar_view, 1, 0)
        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        layout.setColumnStretch(0, 1)
        return page

    def _build_compute_display(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 18)
        layout.setSpacing(14)

        header_layout = QHBoxLayout()
        title_layout = QVBoxLayout()
        title = QLabel("Compute Calibration")
        title.setObjectName("computeTitle")
        subtitle = QLabel("Tổng hợp kết quả tính toán tham số ngoại tại Camera - LiDAR")
        subtitle.setObjectName("computeSubtitle")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout, 1)

        self.compute_status_pill = QLabel("WAITING")
        self.compute_status_pill.setObjectName("computeStatusPill")
        self.compute_status_pill.setAlignment(Qt.AlignCenter)
        self.compute_status_pill.setMinimumWidth(120)
        header_layout.addWidget(self.compute_status_pill, 0, Qt.AlignTop)
        layout.addLayout(header_layout)

        metric_layout = QHBoxLayout()
        metric_layout.setSpacing(12)
        self.compute_metric_labels = {}
        for key, title_text, hint, color in [
            ("samples", "Mẫu hiệu chỉnh", "Dữ liệu được dùng", "#2563eb"),
            ("used", "Điểm tương ứng", "Điểm dùng cho PnP", "#0891b2"),
            ("mean", "Sai số TB", "Mean reprojection", "#dc2626"),
            ("rejected", "Điểm bị loại", "Rejected points", "#16a34a"),
        ]:
            card, value_label, hint_label = self._build_metric_card(title_text, hint, color)
            self.compute_metric_labels[key] = (value_label, hint_label)
            metric_layout.addWidget(card)
        layout.addLayout(metric_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(18)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        table_title = QLabel("Bảng kết quả hiệu chỉnh")
        table_title.setObjectName("computeSectionTitle")
        left_layout.addWidget(table_title)

        self.compute_result_table = QTableWidget(0, 3)
        self.compute_result_table.setHorizontalHeaderLabels(["Nhóm dữ liệu", "Giá trị", "Đơn vị"])
        self.compute_result_table.verticalHeader().setVisible(False)
        self.compute_result_table.setAlternatingRowColors(True)
        self.compute_result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.compute_result_table.setSelectionMode(QTableWidget.NoSelection)
        self.compute_result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.compute_result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.compute_result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        left_layout.addWidget(self.compute_result_table, 1)

        self.compute_log = QPlainTextEdit()
        self.compute_log.setReadOnly(True)
        self.compute_log.setMaximumHeight(150)
        self.compute_log.setPlainText("Compute log will appear here.")
        self.compute_log.setStyleSheet("background: #101820; color: #cbd5e1; border-color: #26384a;")
        left_layout.addWidget(self.compute_log)
        content_layout.addLayout(left_layout, 2)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        matrix_title = QLabel("Tham số hiệu chỉnh")
        matrix_title.setObjectName("computeSectionTitle")
        right_layout.addWidget(matrix_title)

        self.compute_matrix_labels = {}
        for key, title_text, hint, color in [
            ("K", "Ma trận nội tại K", "Đơn vị: pixel", "#2563eb"),
            ("R", "Ma trận quay R", "Biến đổi LiDAR sang camera", "#0891b2"),
            ("T", "Vector tịnh tiến t", "Đơn vị: mm", "#16a34a"),
        ]:
            card, value_label = self._build_matrix_card(title_text, hint, color)
            self.compute_matrix_labels[key] = value_label
            right_layout.addWidget(card)

        self.compute_camera_info_label = QLabel("Camera: chưa có dữ liệu hiệu chỉnh")
        self.compute_camera_info_label.setWordWrap(True)
        self.compute_camera_info_label.setObjectName("pathLabel")
        right_layout.addWidget(self.compute_camera_info_label)
        right_layout.addStretch(1)
        content_layout.addLayout(right_layout, 1)

        layout.addLayout(content_layout, 1)
        self.refresh_compute_results()
        return page

    def _build_metric_card(self, title, hint, color):
        card = QFrame()
        card.setObjectName("metricCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        accent = QFrame()
        accent.setFixedWidth(6)
        accent.setStyleSheet(f"background: {color}; border-radius: 3px;")
        layout.addWidget(accent)

        body_layout = QVBoxLayout()
        body_layout.setContentsMargins(14, 14, 14, 14)
        body_layout.setSpacing(4)
        layout.addLayout(body_layout, 1)

        title_label = QLabel(title)
        title_label.setObjectName("metricTitle")
        value_label = QLabel("--")
        value_label.setObjectName("metricValue")
        hint_label = QLabel(hint)
        hint_label.setObjectName("metricHint")
        hint_label.setWordWrap(True)

        body_layout.addWidget(title_label)
        body_layout.addWidget(value_label)
        body_layout.addWidget(hint_label)
        return card, value_label, hint_label

    def _build_matrix_card(self, title, hint, color):
        card = QFrame()
        card.setObjectName("matrixCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        accent = QFrame()
        accent.setFixedWidth(6)
        accent.setStyleSheet(f"background: {color}; border-radius: 3px;")
        layout.addWidget(accent)

        body_layout = QVBoxLayout()
        body_layout.setContentsMargins(14, 14, 14, 12)
        body_layout.setSpacing(6)
        layout.addLayout(body_layout, 1)

        title_label = QLabel(title)
        title_label.setObjectName("matrixTitle")
        value_label = QLabel("--")
        value_label.setObjectName("matrixValue")
        value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        hint_label = QLabel(hint)
        hint_label.setObjectName("matrixHint")
        hint_label.setWordWrap(True)

        body_layout.addWidget(title_label)
        body_layout.addWidget(value_label)
        body_layout.addWidget(hint_label)
        return card, value_label

    def set_compute_status(self, text, color="#64748b"):
        if hasattr(self, "compute_status_pill"):
            self.compute_status_pill.setText(text)
            self.compute_status_pill.setStyleSheet(
                f"QLabel#computeStatusPill {{ background: {color}; color: #ffffff; }}"
            )

    def set_metric_value(self, key, value, hint=None):
        if not hasattr(self, "compute_metric_labels") or key not in self.compute_metric_labels:
            return
        value_label, hint_label = self.compute_metric_labels[key]
        value_label.setText(str(value))
        if hint is not None:
            hint_label.setText(hint)

    def format_number(self, value, digits=2):
        if value is None:
            return "--"
        try:
            return f"{float(value):.{digits}f}"
        except (TypeError, ValueError):
            return str(value)

    def format_matrix(self, matrix, digits=2):
        if matrix is None:
            return "--"
        arr = np.asarray(matrix, dtype=float)
        if arr.ndim == 1:
            arr = arr.reshape(-1, 1)
        rows = []
        for row in arr:
            rows.append("[ " + "  ".join(f"{value:.{digits}f}" for value in row) + " ]")
        return "\n".join(rows)

    def set_compute_table_rows(self, rows):
        self.compute_result_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                if column_index == 1:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                if row_index in (2, 4) and column_index == 1:
                    item.setForeground(QColor("#dc2626"))
                self.compute_result_table.setItem(row_index, column_index, item)
        self.compute_result_table.resizeRowsToContents()

    def refresh_compute_results(self):
        metrics_data = {}
        npz_data = None
        try:
            if os.path.exists(CALIB_METRICS_FILE):
                with open(CALIB_METRICS_FILE, "r", encoding="utf-8") as f:
                    metrics_data = json.load(f)
            if os.path.exists(CALIB_FILE):
                npz_data = np.load(CALIB_FILE)
        except Exception as exc:
            self.set_compute_status("LOAD ERROR", "#dc2626")
            self.compute_log.appendPlainText(f"Could not load compute result: {exc}")
            return

        if not metrics_data and npz_data is None:
            self.set_compute_status("WAITING", "#64748b")
            self.set_metric_value("samples", "--")
            self.set_metric_value("used", "--")
            self.set_metric_value("mean", "--")
            self.set_metric_value("rejected", "--")
            self.set_compute_table_rows([("Trạng thái", "Chưa có kết quả", "")])
            for label in getattr(self, "compute_matrix_labels", {}).values():
                label.setText("--")
            return

        metrics = metrics_data.get("metrics", {})
        error_stats = metrics.get("reprojection_error_px", {}).get("all", {})
        file_stats = metrics_data.get("file_stats", [])
        used_samples = sum(1 for item in file_stats if item.get("used"))
        if used_samples == 0 and file_stats:
            used_samples = len(file_stats)

        used = metrics.get("used_correspondences")
        rejected = metrics.get("rejected_correspondences")
        mean_error = error_stats.get("mean")
        median_error = error_stats.get("median")
        max_error = error_stats.get("max")
        std_error = error_stats.get("std")

        if used is None and npz_data is not None and "used_indices" in npz_data:
            used = len(npz_data["used_indices"])
        if rejected is None:
            rejected = 0
        if used_samples == 0:
            pair_dir = Path(OUTPUT_DIR) / "pair"
            used_samples = len(list(pair_dir.glob("pair_*.json"))) if pair_dir.is_dir() else "--"

        self.set_compute_status("COMPLETED", "#16a34a")
        self.set_metric_value("samples", used_samples)
        self.set_metric_value("used", used if used is not None else "--")
        self.set_metric_value("mean", self.format_number(mean_error), "Mean reprojection (px)")
        self.set_metric_value("rejected", rejected)

        self.set_compute_table_rows([
            ("Số mẫu hiệu chỉnh", used_samples, "mẫu"),
            ("Điểm tương ứng", used if used is not None else "--", "điểm"),
            ("Sai số trung bình", self.format_number(mean_error), "pixel"),
            ("Sai số trung vị", self.format_number(median_error), "pixel"),
            ("Sai số lớn nhất", self.format_number(max_error), "pixel"),
            ("Độ lệch chuẩn", self.format_number(std_error), "pixel"),
        ])

        if npz_data is not None:
            if "K" in npz_data:
                self.compute_matrix_labels["K"].setText(self.format_matrix(npz_data["K"], 2))
            if "R" in npz_data:
                self.compute_matrix_labels["R"].setText(self.format_matrix(npz_data["R"], 4))
            if "T" in npz_data:
                self.compute_matrix_labels["T"].setText(self.format_matrix(npz_data["T"], 2))
            elif "tvec" in npz_data:
                self.compute_matrix_labels["T"].setText(self.format_matrix(npz_data["tvec"], 2))

        camera_info = metrics_data.get("camera_info", {})
        camera_name = camera_info.get("name") or "Camera"
        serial = camera_info.get("serial_number") or "--"
        firmware = camera_info.get("firmware_version") or "--"
        generated_at = metrics_data.get("generated_at") or "--"
        self.compute_camera_info_label.setText(
            f"Camera: {camera_name} | Serial: {serial} | Firmware: {firmware} | Generated: {generated_at}"
        )

    def _build_fusion_display(self):
        page = QWidget()
        layout = QGridLayout(page)
        self.fusion_overlay_view = ImageView("RGB + LiDAR Overlay")
        self.fusion_dense_depth_view = ImageView("RealSense Depth")
        self.fusion_sparse_depth_view = ImageView("Sparse LiDAR Depth")
        self.fusion_metrics_view = QPlainTextEdit()
        self.fusion_metrics_view.setReadOnly(True)
        self.fusion_metrics_view.setPlainText("Fusion metrics will appear here.")
        self.fusion_metrics_view.setFrameShape(QFrame.StyledPanel)

        layout.addWidget(self.fusion_overlay_view, 0, 0)
        layout.addWidget(self.fusion_dense_depth_view, 0, 1)
        layout.addWidget(self.fusion_sparse_depth_view, 1, 0)
        layout.addWidget(self.fusion_metrics_view, 1, 1)
        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        return page

    def _build_data_display(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.data_preview_stack = QStackedWidget()
        self.data_image_view = ImageView("Select a data folder to preview")
        self.data_text_view = QPlainTextEdit()
        self.data_text_view.setReadOnly(True)
        self.data_text_view.setPlainText("Select a data folder from the right panel.")
        self.data_info_label = QLabel("No data source selected.")
        self.data_info_label.setWordWrap(True)
        self.data_info_label.setObjectName("pathLabel")
        self.data_preview_stack.addWidget(self.data_image_view)
        self.data_preview_stack.addWidget(self.data_text_view)
        layout.addWidget(self.data_preview_stack, 1)
        layout.addWidget(self.data_info_label)
        return page

    def _build_control_panel(self):
        panel = QWidget()
        panel.setObjectName("controlPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel("SensorFusion")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        layout.addWidget(title)

        layout.addWidget(section_label("Mode"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Collect", "Compute", "Fusion", "Data"])
        self.mode_combo.setView(QListView())
        self.mode_combo.view().setSpacing(4)
        for index in range(self.mode_combo.count()):
            self.mode_combo.setItemData(index, QSize(0, 36), Qt.SizeHintRole)
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        layout.addWidget(self.mode_combo)

        self.control_stack = QStackedWidget()
        self.control_stack.addWidget(self._build_collect_controls())
        self.control_stack.addWidget(self._build_compute_controls())
        self.control_stack.addWidget(self._build_fusion_controls())
        self.control_stack.addWidget(self._build_data_controls())
        layout.addWidget(self.control_stack)

        self.status_label = QLabel("State: IDLE")
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumBlockCount(500)
        layout.addWidget(self.log_box, 1)
        return panel

    def _build_collect_controls(self):
        box = QGroupBox("Collect Controls")
        layout = QVBoxLayout(box)

        self.start_btn = set_button_kind(QPushButton("Start Sensors"), "primary")
        self.stop_btn = set_button_kind(QPushButton("Stop Sensors"), "danger")
        self.capture_btn = set_button_kind(QPushButton("Capture Snapshot"), "primary")
        self.reset_btn = set_button_kind(QPushButton("Reset Selection"), "secondary")
        self.accept_btn = set_button_kind(QPushButton("Accept Sample"), "success")
        self.reject_btn = set_button_kind(QPushButton("Reject Sample"), "danger")

        self.start_btn.clicked.connect(self.start_sensors)
        self.stop_btn.clicked.connect(self.stop_sensors)
        self.capture_btn.clicked.connect(self.capture_snapshot)
        self.reset_btn.clicked.connect(self.reset_selection)
        self.accept_btn.clicked.connect(self.accept_sample)
        self.reject_btn.clicked.connect(self.reject_sample)

        for button in [self.start_btn, self.stop_btn, self.capture_btn, self.reset_btn, self.accept_btn, self.reject_btn]:
            layout.addWidget(button)

        guide = QLabel(
            "Flow:\n"
            "1. Start Sensors\n"
            "2. Capture Snapshot\n"
            f"3. Click {REQUIRED_CALIBRATION_POINTS} LiDAR target points\n"
            f"4. Click {REQUIRED_CALIBRATION_POINTS} matching image points\n"
            "5. Accept or Reject\n\n"
            "Use the same order on LiDAR and image: edge endpoint, corner vertex, edge endpoint.\n"
            "LiDAR clicks are saved directly as world-coordinate calibration points."
        )
        guide.setWordWrap(True)
        layout.addWidget(guide)
        layout.addStretch(1)
        return box

    def _build_compute_controls(self):
        box = QGroupBox("Compute Controls")
        layout = QVBoxLayout(box)
        run_btn = set_button_kind(QPushButton("Run Calibration"), "primary")
        run_btn.clicked.connect(lambda: self.run_script("compute_calibration.py"))
        refresh_btn = set_button_kind(QPushButton("Refresh Results"), "secondary")
        refresh_btn.clicked.connect(self.refresh_compute_results)
        layout.addWidget(run_btn)
        layout.addWidget(refresh_btn)
        guide = QLabel("Runs calibration and loads K, R, t plus reprojection metrics into the summary table.")
        guide.setWordWrap(True)
        layout.addWidget(guide)
        layout.addStretch(1)
        return box

    def _build_fusion_controls(self):
        box = QGroupBox("Fusion Controls")
        layout = QVBoxLayout(box)
        self.start_fusion_btn = set_button_kind(QPushButton("Start Fusion"), "primary")
        self.stop_fusion_btn = set_button_kind(QPushButton("Stop Fusion"), "danger")
        self.save_fusion_btn = set_button_kind(QPushButton("Save Frame"), "success")
        self.start_fusion_btn.clicked.connect(self.start_fusion)
        self.stop_fusion_btn.clicked.connect(self.stop_fusion)
        self.save_fusion_btn.clicked.connect(self.save_fusion_frame_ui)

        layout.addWidget(self.start_fusion_btn)
        layout.addWidget(self.stop_fusion_btn)
        layout.addWidget(self.save_fusion_btn)
        guide = QLabel(
            "Fusion runs inside this UI.\n"
            "Left display shows overlay, RealSense depth, sparse LiDAR depth, and metrics.\n"
            "Use Save Frame to store images + metrics JSON."
        )
        guide.setWordWrap(True)
        layout.addWidget(guide)
        layout.addStretch(1)
        return box

    def _build_data_controls(self):
        box = QGroupBox("Data Browser")
        layout = QVBoxLayout(box)
        layout.setSpacing(8)

        layout.addWidget(section_label("1. Data group"))

        self.data_category_layout = QVBoxLayout()
        self.data_category_layout.setSpacing(6)
        layout.addLayout(self.data_category_layout)

        layout.addWidget(section_label("2. Source folder"))

        source_frame = QFrame()
        source_frame.setObjectName("sourceFrame")
        source_layout = QVBoxLayout(source_frame)
        source_layout.setContentsMargins(8, 8, 8, 8)
        source_layout.setSpacing(8)

        self.data_path_label = QLabel("Select a data group above.")
        self.data_path_label.setWordWrap(True)
        self.data_path_label.setObjectName("pathLabel")
        source_layout.addWidget(self.data_path_label)

        self.data_back_btn = set_button_kind(QPushButton("Back"), "secondary")
        self.data_back_btn.clicked.connect(self.go_data_parent)
        source_layout.addWidget(self.data_back_btn)

        self.data_file_list = QListWidget()
        self.data_file_list.itemClicked.connect(self.on_data_item_clicked)
        source_layout.addWidget(self.data_file_list, 1)

        layout.addWidget(source_frame, 1)

        nav_layout = QHBoxLayout()
        prev_btn = set_button_kind(QPushButton("Previous"), "secondary")
        next_btn = set_button_kind(QPushButton("Next"), "secondary")
        prev_btn.clicked.connect(self.show_previous_data_image)
        next_btn.clicked.connect(self.show_next_data_image)
        nav_layout.addWidget(prev_btn)
        nav_layout.addWidget(next_btn)
        layout.addLayout(nav_layout)

        hint = QLabel("Previous/Next changes the current timestamp in the selected source.")
        hint.setWordWrap(True)
        hint.setObjectName("pathLabel")
        layout.addWidget(hint)

        self.populate_data_categories()
        self.populate_data_browser(os.path.join(PROJECT_ROOT, "data"), root_only=True)
        return box

    def on_mode_changed(self, index):
        self.display_stack.setCurrentIndex(index)
        self.control_stack.setCurrentIndex(index)
        if index == 1:
            self.refresh_compute_results()

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_box.appendPlainText(f"[{timestamp}] {message}")

    def set_state(self, state):
        self.state = state
        self.status_label.setText(f"State: {state} | Samples saved: {self.sample_count}")

    def start_sensors(self):
        if self.camera_worker is None:
            self.camera_worker = CameraWorker()
            self.camera_worker.frame_ready.connect(self.on_camera_frame)
            self.camera_worker.status.connect(self.log)
            self.camera_worker.start()

        if self.lidar_worker is None:
            self.lidar_worker = LidarWorker(LIDAR_PORT)
            self.lidar_worker.scan_ready.connect(self.on_lidar_scan)
            self.lidar_worker.status.connect(self.log)
            self.lidar_worker.start()

        self.set_state("STREAMING")
        self.log("Sensors starting...")

    def stop_sensors(self):
        if self.camera_worker is not None:
            self.camera_worker.stop()
            self.camera_worker = None
        if self.lidar_worker is not None:
            self.lidar_worker.stop()
            self.lidar_worker = None
        self.set_state("IDLE")
        self.log("Sensors stopped")

    def on_camera_frame(self, color_img, depth_img):
        self.latest_color = color_img
        self.latest_depth = depth_img
        if self.state == "STREAMING":
            self.camera_view.set_image(color_img)

    def on_lidar_scan(self, filtered_scan, display_scan, raw_scan_count, debug):
        self.latest_scan = filtered_scan
        self.latest_display_scan = display_scan
        self.latest_lidar_debug = debug
        self.latest_raw_scan_count = raw_scan_count
        if self.state == "STREAMING":
            self.lidar_view.set_points(
                display_scan,
                debug_metrics=debug,
            )

    def capture_snapshot(self):
        if self.latest_color is None or self.latest_depth is None:
            self.log("Cannot capture: no camera frame yet")
            return
        if not self.latest_display_scan:
            self.log("Cannot capture: no LiDAR display scan yet")
            return

        self.snapshot_color = self.latest_color.copy()
        self.snapshot_depth = self.latest_depth.copy()
        self.snapshot_lidar = list(self.latest_display_scan)
        self.lidar_raw_clicks = []
        self.lidar_selected = []
        self.lidar_feature_extraction = None
        self.image_selected = []
        self.correspondences = []
        self.preview_img = None

        self.camera_view.set_image(self.snapshot_color)
        self.lidar_view.set_points(
            self.snapshot_lidar,
            debug_metrics={
                "source": "captured display-smoothed snapshot",
                "display_points": len(self.snapshot_lidar),
                "smooth_scans": self.latest_lidar_debug.get("smooth_scans"),
                "smooth_angle_bin_deg": self.latest_lidar_debug.get("smooth_angle_bin_deg"),
            },
        )
        self.lidar_view.set_manual_clicks([])
        self.lidar_view.set_feature_overlay([], [], [], [])
        self.set_state("SNAPSHOT_CAPTURED")
        self.log(
            "Snapshot captured. "
            f"Raw points: {self.latest_raw_scan_count}, "
            f"filtered points: {len(self.latest_scan)}, "
            f"display-smoothed points used for fitting: {len(self.snapshot_lidar)}"
        )
        self.log(
            "Snapshot uses the same LiDAR points shown on the plot: "
            f"smoothing scans={self.latest_lidar_debug.get('smooth_scans')}, "
            f"angle bin={self.latest_lidar_debug.get('smooth_angle_bin_deg')} deg."
        )
        self.log(
            "Click 3 LiDAR guide points on the corner target: left edge, corner, right edge. "
            "The system will fit target lines and create 3 calibration feature points."
        )

    def on_lidar_clicked(self, click):
        if self.state not in ["SNAPSHOT_CAPTURED", "SELECTING_LIDAR", "SELECTING_IMAGE"]:
            return
        if len(self.lidar_raw_clicks) >= REQUIRED_CALIBRATION_POINTS:
            return

        self.lidar_raw_clicks.append(click)
        self.lidar_view.set_manual_clicks(self.lidar_raw_clicks)
        self.log(
            f"LiDAR guide C{len(self.lidar_raw_clicks)}: "
            f"x={click['x_mm']:.1f} mm, z={click['z_mm']:.1f} mm"
        )

        if len(self.lidar_raw_clicks) == REQUIRED_CALIBRATION_POINTS:
            try:
                features, diagnostics = extract_corner_features(self.snapshot_lidar, self.lidar_raw_clicks)
            except ValueError as exc:
                self.log(f"LiDAR feature fitting failed: {exc}")
                self.lidar_raw_clicks = []
                self.lidar_selected = []
                self.lidar_feature_extraction = None
                self.lidar_view.set_manual_clicks([])
                self.lidar_view.set_feature_overlay([], [], [], [])
                self.set_state("SNAPSHOT_CAPTURED")
                return

            self.lidar_selected = features
            self.lidar_feature_extraction = diagnostics
            lines = [diagnostics.get("left_line"), diagnostics.get("right_line")]
            support_points = diagnostics.get("left_support_points", []) + diagnostics.get("right_support_points", [])
            inlier_points = diagnostics.get("left_inlier_points", []) + diagnostics.get("right_inlier_points", [])
            self.lidar_view.set_feature_overlay(
                features,
                lines,
                support_points=support_points,
                inlier_points=inlier_points,
            )
            self.set_state("SELECTING_IMAGE")
            left_fit = diagnostics.get("left_line_fit", {})
            right_fit = diagnostics.get("right_line_fit", {})
            left_residual = left_fit.get("residuals", {}).get("median_mm")
            right_residual = right_fit.get("residuals", {}).get("median_mm")
            self.log(
                "LiDAR features fitted: "
                f"left inliers={diagnostics.get('left_inlier_count')}/{diagnostics.get('left_support_count')}, "
                f"right inliers={diagnostics.get('right_inlier_count')}/{diagnostics.get('right_support_count')}, "
                f"median residual L/R={left_residual}/{right_residual} mm"
            )
            self.log(f"Now click {REQUIRED_CALIBRATION_POINTS} matching points on the camera image.")
        else:
            self.set_state("SELECTING_LIDAR")

    def on_image_clicked(self, x, y):
        if self.state not in ["SELECTING_IMAGE", "SNAPSHOT_CAPTURED"]:
            return
        if len(self.lidar_selected) < REQUIRED_CALIBRATION_POINTS:
            self.log(f"Select {REQUIRED_CALIBRATION_POINTS} LiDAR points before selecting image points")
            return
        if len(self.image_selected) >= REQUIRED_CALIBRATION_POINTS:
            return

        self.image_selected.append((x, y))
        self.log(f"Image P{len(self.image_selected)}: ({x}, {y})")
        self._refresh_image_selection()

        if len(self.image_selected) == REQUIRED_CALIBRATION_POINTS:
            self.prepare_preview()

    def _refresh_image_selection(self):
        if self.snapshot_color is None:
            return
        image = self.snapshot_color.copy()
        colors = [(0, 255, 0), (0, 220, 255), (0, 0, 255)]
        for idx in range(len(self.image_selected) - 1):
            cv2.line(image, self.image_selected[idx], self.image_selected[idx + 1], (255, 255, 0), 2)
        for idx, point in enumerate(self.image_selected):
            color = colors[idx % len(colors)]
            cv2.circle(image, point, 6, color, -1)
            cv2.putText(image, f"P{idx + 1}", (point[0] + 8, point[1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        self.camera_view.set_image(image)

    def prepare_preview(self):
        if (
            len(self.image_selected) != REQUIRED_CALIBRATION_POINTS
            or len(self.lidar_selected) != REQUIRED_CALIBRATION_POINTS
        ):
            return

        try:
            self.correspondences = build_correspondences(self.lidar_selected, self.image_selected)
        except ValueError as exc:
            self.log(f"Cannot prepare sample: {exc}")
            return

        self.preview_img = render_pair_preview(
            self.snapshot_color,
            self.correspondences,
        )
        self.camera_view.set_image(self.preview_img)
        self.set_state("PREVIEW_READY")
        self.log(f"Preview ready. Direct correspondences: {len(self.correspondences)}")

    def reset_selection(self):
        self.lidar_selected = []
        self.lidar_raw_clicks = []
        self.lidar_feature_extraction = None
        self.image_selected = []
        self.correspondences = []
        self.preview_img = None
        self.lidar_view.set_manual_clicks([])
        self.lidar_view.set_feature_overlay([], [], [], [])
        if self.snapshot_color is not None:
            self.camera_view.set_image(self.snapshot_color)
            self.set_state("SNAPSHOT_CAPTURED")
        self.log("Selection reset")

    def accept_sample(self):
        if self.state != "PREVIEW_READY" or self.preview_img is None:
            self.log("No preview ready to save")
            return

        timestamp = int(time.time() * 1000)
        project_config = {
            "lidar_port": LIDAR_PORT,
            "color_width": COLOR_WIDTH,
            "color_height": COLOR_HEIGHT,
            "depth_width": DEPTH_WIDTH,
            "depth_height": DEPTH_HEIGHT,
            "fps": CAMERA_FPS,
            "camera_lidar_vertical_offset_mm": 80,
            "camera_lidar_forward_offset_mm": 20,
            "lidar_snapshot_source": "captured_display_smoothed_scan",
            "realtime_preview_method": "short_window_median_angle_binning_for_display_and_fitting",
            "realtime_preview_smooth_scans": DISPLAY_SMOOTH_SCAN_COUNT,
            "realtime_preview_angle_bin_deg": DISPLAY_SMOOTH_ANGLE_BIN_DEG,
        }
        calibration_data = build_calibration_data(
            timestamp,
            self.correspondences,
            project_config,
            manual_lidar_clicks=self.lidar_raw_clicks,
            lidar_feature_extraction=self.lidar_feature_extraction,
        )
        paths = save_sample(
            OUTPUT_DIR,
            self.snapshot_color,
            self.snapshot_depth,
            self.preview_img,
            calibration_data,
            timestamp,
        )
        self.sample_count += 1
        self.log(f"Sample saved: {os.path.relpath(paths['pair_json'], PROJECT_ROOT)}")
        self.resume_stream()

    def reject_sample(self):
        if self.state == "STREAMING":
            return
        self.log("Sample rejected")
        self.resume_stream()

    def resume_stream(self):
        self.snapshot_color = None
        self.snapshot_depth = None
        self.snapshot_lidar = []
        self.lidar_raw_clicks = []
        self.lidar_selected = []
        self.lidar_feature_extraction = None
        self.image_selected = []
        self.correspondences = []
        self.preview_img = None
        self.lidar_view.set_manual_clicks([])
        self.lidar_view.set_feature_overlay([], [], [], [])
        self.set_state("STREAMING" if self.camera_worker or self.lidar_worker else "IDLE")
    def run_script(self, script_name):
        if self.process is not None:
            self.log("Another process is already running")
            return

        script_path = os.path.join(PROJECT_ROOT, "src", script_name)
        self.process = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONIOENCODING", "utf-8")
        self.process.setProcessEnvironment(env)
        self.process.setWorkingDirectory(PROJECT_ROOT)
        self.process.setProgram(sys.executable)
        self.process.setArguments([script_path])
        self.process.readyReadStandardOutput.connect(self.on_process_output)
        self.process.readyReadStandardError.connect(self.on_process_output)
        self.process.finished.connect(self.on_process_finished)
        self.process_script_name = script_name
        if script_name == "compute_calibration.py":
            self.compute_log.clear()
            self.set_compute_status("RUNNING", "#2563eb")
        self.process.start()
        self.log(f"Started {script_name}")

    def on_process_output(self):
        if self.process is None:
            return
        output = bytes(self.process.readAllStandardOutput()).decode(errors="replace")
        error = bytes(self.process.readAllStandardError()).decode(errors="replace")
        text = output + error
        if text:
            if self.display_stack.currentIndex() == 1:
                self.compute_log.appendPlainText(text.rstrip())
            self.log(text.rstrip())

    def on_process_finished(self):
        finished_script = self.process_script_name
        self.log("Process finished")
        self.process = None
        self.process_script_name = None
        if finished_script == "compute_calibration.py":
            self.refresh_compute_results()

    def data_display_name(self, path):
        name = Path(path).name
        return name.replace("_", " ").title() if Path(path).is_dir() else name

    def data_root(self):
        return os.path.abspath(os.path.join(PROJECT_ROOT, "data"))

    def clear_data_category_buttons(self):
        while self.data_category_layout.count():
            item = self.data_category_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def populate_data_categories(self):
        self.clear_data_category_buttons()
        data_root = Path(PROJECT_ROOT) / "data"
        if not data_root.is_dir():
            self.data_path_label.setText(f"Data folder not found: {data_root}")
            return

        root_dirs = [p for p in sorted(data_root.iterdir(), key=lambda p: p.name.lower()) if p.is_dir()][:3]
        for path in root_dirs:
            button = QPushButton(self.data_display_name(path))
            button.setObjectName("categoryButton")
            button.clicked.connect(lambda _, p=str(path): self.select_data_group(p))
            self.data_category_layout.addWidget(button)

    def reset_data_preview(self, message):
        self.data_files = []
        self.data_index = 0
        self.data_preview_stack.setCurrentIndex(0)
        self.data_image_view.clear_image(message)
        self.data_text_view.clear()

    def data_file_key(self, path):
        stem = Path(path).stem
        matches = re.findall(r"\d+", stem)
        return matches[-1] if matches else stem

    def data_preview_kinds(self, folder):
        if not os.path.isdir(folder):
            return []
        files = [p for p in Path(folder).iterdir() if p.is_file()]
        kinds = []
        if any(p.suffix.lower() in IMAGE_EXTS for p in files):
            kinds.append("image")
        if any(p.suffix.lower() in TEXT_EXTS for p in files):
            kinds.append("text")
        return kinds

    def collect_preview_files(self, folder, kind=None):
        files = [p for p in sorted(Path(folder).iterdir()) if p.is_file()]
        if kind == "image":
            return [str(p) for p in files if p.suffix.lower() in IMAGE_EXTS]
        if kind == "text":
            return [str(p) for p in files if p.suffix.lower() in TEXT_EXTS]

        images = [str(p) for p in files if p.suffix.lower() in IMAGE_EXTS]
        texts = [str(p) for p in files if p.suffix.lower() in TEXT_EXTS]
        return images if images else texts

    def populate_data_browser(self, folder=None, root_only=False):
        if root_only:
            self.show_data_root()
            return

        if folder is not None:
            self.select_data_group(folder)

    def show_data_root(self):
        self.data_file_list.clear()
        self.data_group_dir = None
        self.data_browser_level = "root"
        self.reset_data_preview("Choose a source folder from the right panel.")
        self.data_path_label.setText("Select one of the three data groups above.")
        self.data_back_btn.setEnabled(False)
        self.data_info_label.setText("Data Browser ready.")

    def select_data_group(self, folder):
        folder = os.path.abspath(folder)
        if not os.path.isdir(folder):
            self.data_info_label.setText(f"Folder not found: {folder}")
            return

        self.data_file_list.clear()
        self.data_group_dir = folder
        self.data_browser_level = "group"
        self.reset_data_preview("Choose a folder from the right panel.")

        rel = os.path.relpath(folder, PROJECT_ROOT)
        self.data_path_label.setText(rel)
        entries = sorted(Path(folder).iterdir(), key=lambda p: p.name.lower())
        shown_dirs = 0
        for path in entries:
            if path.is_dir():
                item = QListWidgetItem(self.data_display_name(path))
                item.setData(Qt.UserRole, {"kind": "folder", "path": str(path)})
                self.data_file_list.addItem(item)
                shown_dirs += 1

        preview_files = self.collect_preview_files(folder)
        if preview_files and shown_dirs == 0:
            self.select_data_folder(folder)
            return

        self.data_back_btn.setEnabled(True)
        if shown_dirs == 0:
            self.data_info_label.setText(f"No supported folders/files in: {rel}")
        else:
            self.data_info_label.setText(f"{shown_dirs} folder(s) in {rel}")

    def select_data_folder(self, folder):
        folder = os.path.abspath(folder)
        if not os.path.isdir(folder):
            self.data_info_label.setText(f"Folder not found: {folder}")
            return

        previous_key = self.data_current_key
        previous_index = self.data_index
        self.data_path_label.setText(os.path.relpath(folder, PROJECT_ROOT))
        kinds = self.data_preview_kinds(folder)

        if not kinds:
            self.data_info_label.setText(f"No preview files found in: {os.path.relpath(folder, PROJECT_ROOT)}")
            return

        if len(kinds) > 1:
            self.populate_data_type_choices(folder, kinds)
        else:
            self.data_browser_level = "group"

        preferred_kind = "image" if "image" in kinds else kinds[0]
        self.load_data_folder(
            folder,
            kind=preferred_kind,
            preferred_key=previous_key,
            preferred_index=previous_index,
        )

    def populate_data_type_choices(self, folder, kinds):
        self.data_file_list.clear()
        self.data_browser_level = "type"
        self.data_path_label.setText(os.path.relpath(folder, PROJECT_ROOT))
        for kind in kinds:
            label = "Preview Image" if kind == "image" else "JSON / Text"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, {"kind": kind, "path": folder})
            self.data_file_list.addItem(item)
        self.data_back_btn.setEnabled(True)

    def on_data_item_clicked(self, item):
        payload = item.data(Qt.UserRole)
        if not isinstance(payload, dict):
            return

        kind = payload.get("kind")
        path = payload.get("path")
        if kind == "folder":
            self.select_data_folder(path)
        elif kind in {"image", "text"}:
            self.load_data_folder(
                path,
                kind=kind,
                preferred_key=self.data_current_key,
                preferred_index=self.data_index,
            )

    def go_data_parent(self):
        if self.data_browser_level == "type" and self.data_group_dir:
            self.select_data_group(self.data_group_dir)
            return
        self.show_data_root()

    def load_data_folder(self, folder, preferred_key=None, preferred_index=0, kind=None):
        if not os.path.isdir(folder):
            self.data_files = []
            self.data_index = 0
            self.data_info_label.setText(f"Folder not found: {folder}")
            self.log(f"Data folder not found: {folder}")
            return

        self.data_files = self.collect_preview_files(folder, kind=kind)
        self.data_index = 0
        if preferred_key is not None and self.data_files:
            for index, file_path in enumerate(self.data_files):
                if self.data_file_key(file_path) == preferred_key:
                    self.data_index = index
                    break
            else:
                self.data_index = min(max(preferred_index, 0), len(self.data_files) - 1)
        elif self.data_files:
            self.data_index = min(max(preferred_index, 0), len(self.data_files) - 1)

        if not self.data_files:
            self.data_info_label.setText(f"No preview files found in: {folder}")
            self.log(f"No preview files found in: {folder}")
            return

        self.display_stack.setCurrentIndex(3)
        self.control_stack.setCurrentIndex(3)
        self.mode_combo.setCurrentIndex(3)
        self.show_data_file()
        self.log(f"Loaded {len(self.data_files)} preview files from {folder}")

    def show_text_file(self, path, update_key=True):
        try:
            with open(path, "r", encoding="utf-8") as file:
                text = file.read()
            if path.lower().endswith(".json"):
                try:
                    text = json.dumps(json.loads(text), indent=2, ensure_ascii=False)
                except json.JSONDecodeError:
                    pass
        except Exception as exc:
            text = f"Cannot read file:\n{path}\n\n{exc}"

        self.data_preview_stack.setCurrentIndex(1)
        self.data_text_view.setPlainText(text)
        if update_key:
            self.data_current_key = self.data_file_key(path)
        rel_path = os.path.relpath(path, PROJECT_ROOT)
        self.data_info_label.setText(rel_path)
        self.log(f"Opened text file: {rel_path}")

    def show_data_file(self):
        if not self.data_files:
            self.data_info_label.setText("No data folder loaded.")
            return

        path = self.data_files[self.data_index]
        self.data_current_key = self.data_file_key(path)
        suffix = Path(path).suffix.lower()
        if suffix in TEXT_EXTS:
            self.show_text_file(path, update_key=False)
            self.data_info_label.setText(
                f"{self.data_index + 1}/{len(self.data_files)} | {os.path.relpath(path, PROJECT_ROOT)}"
            )
            return

        image = prepare_image_for_display(imread_unicode(path))
        if image is None:
            self.data_info_label.setText(f"Cannot read image: {path}")
            self.log(f"Cannot read image: {path}")
            return

        self.data_preview_stack.setCurrentIndex(0)
        self.data_image_view.set_image(image)
        rel_path = os.path.relpath(path, PROJECT_ROOT)
        self.data_info_label.setText(
            f"{self.data_index + 1}/{len(self.data_files)} | {rel_path}"
        )

    def show_previous_data_image(self):
        if not self.data_files:
            return
        self.data_index = (self.data_index - 1) % len(self.data_files)
        self.show_data_file()

    def show_next_data_image(self):
        if not self.data_files:
            return
        self.data_index = (self.data_index + 1) % len(self.data_files)
        self.show_data_file()

    def start_fusion(self):
        if self.fusion_worker is not None:
            self.log("Fusion is already running")
            return

        if self.camera_worker is not None or self.lidar_worker is not None:
            self.log("Stopping collect sensors before starting fusion")
            self.stop_sensors()

        self.fusion_worker = FusionWorker(LIDAR_PORT, CALIB_FILE)
        self.fusion_worker.frame_ready.connect(self.on_fusion_frame)
        self.fusion_worker.status.connect(self.log)
        self.fusion_worker.start()
        self.set_state("FUSION_RUNNING")
        self.log("Fusion worker starting...")

    def stop_fusion(self):
        if self.fusion_worker is not None:
            self.fusion_worker.stop()
            self.fusion_worker = None
        self.set_state("IDLE")
        self.log("Fusion stopped by user")

    def on_fusion_frame(self, color_img, depth_img, overlay, sparse_depth, dense_cm, metrics):
        self.latest_fusion_color = color_img
        self.latest_fusion_depth = depth_img
        self.latest_fusion_overlay = overlay
        self.latest_fusion_sparse = sparse_depth
        self.latest_fusion_metrics = metrics

        self.fusion_overlay_view.set_image(overlay)
        self.fusion_dense_depth_view.set_image(dense_cm)
        self.fusion_sparse_depth_view.set_image(prepare_image_for_display(sparse_depth))
        self.fusion_metrics_view.setPlainText(metrics_to_text(metrics))

    def save_fusion_frame_ui(self):
        if self.latest_fusion_overlay is None or self.latest_fusion_metrics is None:
            self.log("No fusion frame available to save")
            return

        timestamp = int(time.time() * 1000)
        paths = save_fusion_frame(
            FUSION_OUTPUT_DIR,
            PROJECT_ROOT,
            CALIB_FILE,
            LIDAR_PORT,
            self.latest_fusion_color,
            self.latest_fusion_depth,
            self.latest_fusion_sparse,
            self.latest_fusion_overlay,
            self.latest_fusion_metrics,
            timestamp,
        )
        self.log(f"Fusion frame saved: {os.path.relpath(paths['metrics'], PROJECT_ROOT)}")

    def closeEvent(self, event):
        self.stop_sensors()
        self.stop_fusion()
        if self.process is not None:
            self.process.kill()
            self.process = None
            self.process_script_name = None
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = SensorFusionUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
