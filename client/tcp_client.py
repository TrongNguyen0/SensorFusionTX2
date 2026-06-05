import argparse
import socket
import struct
import time

import cv2
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description="TCP client for Jetson fusion stream")
    parser.add_argument("--host", required=True, help="Jetson IP address")
    parser.add_argument("--port", type=int, default=9999)
    parser.add_argument("--reconnect-delay", type=float, default=2.0)
    return parser.parse_args()


def recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks = []
    remaining = size
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("connection closed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def connect(host: str, port: int, reconnect_delay: float) -> socket.socket:
    while True:
        try:
            print("Connecting to {}:{}...".format(host, port))
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            print("Connected")
            return sock
        except Exception as exc:
            print("Connect failed: {}. Retry in {:.1f}s".format(exc, reconnect_delay))
            time.sleep(reconnect_delay)


def main() -> None:
    args = parse_args()
    sock = None

    try:
        while True:
            if sock is None:
                sock = connect(args.host, args.port, args.reconnect_delay)

            try:
                header = recv_exact(sock, 4)
                frame_size = struct.unpack("!I", header)[0]
                frame_bytes = recv_exact(sock, frame_size)

                encoded = np.frombuffer(frame_bytes, dtype=np.uint8)
                frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
                if frame is None:
                    print("Decode failed")
                    continue

                cv2.imshow("Jetson Sensor Fusion", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q"), 27):
                    break

            except Exception as exc:
                print("Receive failed: {}".format(exc))
                try:
                    sock.close()
                except Exception:
                    pass
                sock = None

    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
