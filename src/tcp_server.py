import logging
import socket
import struct
import threading
from typing import Optional

import cv2
import numpy as np


class TcpFrameServer(object):
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 9999,
        jpeg_quality: int = 80,
    ) -> None:
        self.host = host
        self.port = port
        self.jpeg_quality = jpeg_quality
        self.logger = logging.getLogger(self.__class__.__name__)
        self._server_socket = None
        self._client_socket = None
        self._running = False
        self._thread = None
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._running:
            return

        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(1)
        self._server_socket.settimeout(1.0)

        self._running = True
        self._thread = threading.Thread(target=self._accept_loop)
        self._thread.daemon = True
        self._thread.start()
        self.logger.info("TCP server listening on %s:%d", self.host, self.port)

    def stop(self) -> None:
        self._running = False
        with self._lock:
            self._close_client_locked()
        if self._server_socket is not None:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def send_frame(self, frame: np.ndarray) -> bool:
        with self._lock:
            client = self._client_socket
            if client is None:
                return False

            ok, encoded = cv2.imencode(
                ".jpg",
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), int(self.jpeg_quality)],
            )
            if not ok:
                self.logger.warning("JPEG encode failed")
                return False

            payload = encoded.tobytes()
            packet = struct.pack("!I", len(payload)) + payload

            try:
                client.sendall(packet)
                return True
            except Exception as exc:
                self.logger.warning("TCP send failed: %s", exc)
                self._close_client_locked()
                return False

    def _accept_loop(self) -> None:
        while self._running:
            try:
                client, address = self._server_socket.accept()
                client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                with self._lock:
                    self._close_client_locked()
                    self._client_socket = client
                self.logger.info("TCP client connected: %s", address)
            except socket.timeout:
                continue
            except OSError:
                break
            except Exception as exc:
                self.logger.warning("TCP accept failed: %s", exc)

    def _close_client_locked(self) -> None:
        if self._client_socket is None:
            return
        try:
            self._client_socket.close()
        except Exception:
            pass
        self._client_socket = None

    def __enter__(self) -> "TcpFrameServer":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
