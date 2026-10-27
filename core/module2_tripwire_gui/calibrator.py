"""
MODULE 2: BỘ CẤU HÌNH VẠCH ẢO TƯƠNG TÁC (INTERACTIVE TRIPWIRE CALIBRATOR)
Môn học: Xử lý ảnh (Digital Image Processing) - PTIT HCM
Giảng viên phụ trách: TS. Huỳnh Trung Trụ
"""

import json
import os
from typing import Tuple, Optional, List
import cv2
import numpy as np


class TripwireCalibrator:
    """
    Bộ hỗ trợ cấu hình vạch ảo:
    1. Cửa sổ OpenCV tương tác click chuột trực tiếp trên khung hình.
    2. Lưu / Đọc cấu hình từ file JSON (data/configs/tripwire_config.json).
    3. Hỗ trợ cấu hình mặc định tương ứng với độ phân giải video.
    """

    def __init__(self, config_path: str = "data/configs/tripwire_config.json"):
        self.config_path = config_path
        self._click_points: List[Tuple[int, int]] = []

    def load_config(self) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Tải tọa độ vạch ảo từ file cấu hình nếu tồn tại."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    p1 = tuple(data["pt1"])
                    p2 = tuple(data["pt2"])
                    return ((int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])))
            except Exception as e:
                print(f"[Cảnh báo] Không thể đọc {self.config_path}: {e}")
        return None

    def save_config(self, line_coords: Tuple[Tuple[int, int], Tuple[int, int]], d_threshold: float = 35.0) -> None:
        """Lưu tọa độ vạch ảo vào file cấu hình JSON."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        data = {
            "pt1": [int(line_coords[0][0]), int(line_coords[0][1])],
            "pt2": [int(line_coords[1][0]), int(line_coords[1][1])],
            "d_threshold": float(d_threshold)
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def calibrate_with_opencv(
        self,
        video_source: str,
        window_name: str = "MODULE 2: TRIPWIRE CALIBRATION"
    ) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """
        Khởi tạo cửa sổ xem trước OpenCV để người dùng click 2 điểm tạo vạch ảo.
        Phím tắt:
        - Chuột trái: Chọn điểm
        - 'R': Đặt lại (Reset)
        - SPACE: Xác nhận lưu và hoàn tất
        - ESC: Hủy và dùng mặc định
        """
        cap = cv2.VideoCapture(video_source)
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            print("[Calibrator] Không đọc được frame từ nguồn video! Dùng vạch mặc định.")
            return ((100, 240), (550, 240))

        h, w = frame.shape[:2]
        default_line = ((int(w * 0.15), int(h * 0.5)), (int(w * 0.85), int(h * 0.5)))
        self._click_points = []

        def _mouse_cb(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                if len(self._click_points) < 2:
                    self._click_points.append((int(x), int(y)))

        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, _mouse_cb)

        print("[Calibrator] Hướng dẫn: Click 2 điểm để tạo vạch. Nhấn [SPACE] để xác nhận, [R] để reset.")

        while True:
            display = frame.copy()
            cv2.putText(
                display,
                "Click 2 diem de tao Vach Ao. Nhan [SPACE] de xong, [R] de Reset",
                (15, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 255),
                2
            )

            for pt in self._click_points:
                cv2.circle(display, pt, 6, (0, 0, 255), -1)

            if len(self._click_points) == 2:
                cv2.line(display, self._click_points[0], self._click_points[1], (0, 255, 0), 2)
                cv2.putText(
                    display,
                    "DA CHON 2 DIEM! Nhan [SPACE] de bat dau",
                    (15, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 255, 0),
                    2
                )

            cv2.imshow(window_name, display)
            key = cv2.waitKey(20) & 0xFF

            if key == ord('r') or key == ord('R'):
                self._click_points = []
            elif key == 32:  # SPACE
                if len(self._click_points) == 2:
                    break
            elif key == 27:  # ESC
                break

        cv2.destroyWindow(window_name)

        if len(self._click_points) == 2:
            chosen_line = (self._click_points[0], self._click_points[1])
            self.save_config(chosen_line)
            return chosen_line

        # Thử đọc từ config cũ hoặc dùng mặc định
        cached = self.load_config()
        return cached if cached else default_line
