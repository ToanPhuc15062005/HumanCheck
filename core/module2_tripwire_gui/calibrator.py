"""
MODULE 2: BỘ CẤU HÌNH VẠCH ẢO TƯƠNG TÁC (INTERACTIVE TRIPWIRE CALIBRATOR)
Môn học: Xử lý ảnh (Digital Image Processing) - PTIT HCM
Giảng viên phụ trách: TS. Huỳnh Trung Trụ
"""

import json
import os
import sys
from typing import Tuple, Optional, List, Union, Any
import cv2
import numpy as np


def normalize_video_source(src: Any) -> Union[int, str]:
    """
    Chuẩn hóa nguồn video: chuyển chuỗi số thành int (ví dụ: '0' -> 0).
    Giữ nguyên đường dẫn file hoặc URL RTSP/HTTP.
    """
    if isinstance(src, str):
        stripped = src.strip()
        if stripped.isdigit():
            return int(stripped)
        return stripped
    return src


class TripwireCalibrator:
    """
    Bộ hỗ trợ cấu hình vạch ảo:
    1. Cửa sổ OpenCV tương tác click chuột trực tiếp trên khung hình.
    2. Lưu / Đọc cấu hình từ file JSON (data/configs/tripwire_config.json & cameras_profile.json).
    3. Hỗ trợ cấu hình mặc định tương ứng với độ phân giải video.
    """

    def __init__(
        self,
        config_path: str = "data/configs/tripwire_config.json",
        profile_path: str = "data/configs/cameras_profile.json"
    ):
        self.config_path = config_path
        self.profile_path = profile_path
        self._click_points: List[Tuple[int, int]] = []

    def load_config(
        self,
        source: Optional[Union[int, str]] = None
    ) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """
        Tải tọa độ vạch ảo:
        1. Ưu tiên đọc từ cameras_profile.json theo source cụ thể.
        2. Fallback đọc từ tripwire_config.json.
        """
        norm_src = str(normalize_video_source(source)) if source is not None else None

        # 1. Thử đọc từ cameras_profile.json
        if norm_src and os.path.exists(self.profile_path):
            try:
                with open(self.profile_path, "r", encoding="utf-8") as f:
                    pdata = json.load(f)
                    profiles = pdata.get("profiles", {})
                    if norm_src in profiles:
                        prof = profiles[norm_src]
                        p1 = tuple(prof["pt1"])
                        p2 = tuple(prof["pt2"])
                        return ((int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])))
            except Exception as e:
                print(f"[Cảnh báo] Không thể đọc profile từ {self.profile_path}: {e}")

        # 2. Fallback đọc từ tripwire_config.json
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

    def save_config(
        self,
        line_coords: Tuple[Tuple[int, int], Tuple[int, int]],
        d_threshold: float = 35.0,
        source: Optional[Union[int, str]] = None
    ) -> None:
        """
        Lưu cấu hình vạch ảo theo cơ chế Dual-Write:
        1. Ghi đè vào tripwire_config.json (Active config truyền thống).
        2. Đồng bộ vào profile tương ứng trong cameras_profile.json.
        """
        p1 = [int(line_coords[0][0]), int(line_coords[0][1])]
        p2 = [int(line_coords[1][0]), int(line_coords[1][1])]
        thresh = float(d_threshold)

        # 1. Ghi vào tripwire_config.json
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        data = {
            "pt1": p1,
            "pt2": p2,
            "d_threshold": thresh
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        # 2. Ghi vào cameras_profile.json (Dual-Write)
        src_key = str(normalize_video_source(source)) if source is not None else "default"
        src_type = "webcam" if (isinstance(source, int) or (isinstance(source, str) and source.isdigit())) else (
            "rtsp" if str(source).startswith(("rtsp://", "http://")) else "file"
        )
        display_name = f"Webcam Cổng {source}" if src_type == "webcam" else (
            "IP Camera" if src_type == "rtsp" else os.path.basename(str(source or "default"))
        )

        profiles_data = {"active_source": src_key, "profiles": {}}
        if os.path.exists(self.profile_path):
            try:
                with open(self.profile_path, "r", encoding="utf-8") as f:
                    profiles_data = json.load(f)
            except Exception:
                profiles_data = {"active_source": src_key, "profiles": {}}

        profiles_data["active_source"] = src_key
        if "profiles" not in profiles_data:
            profiles_data["profiles"] = {}

        profiles_data["profiles"][src_key] = {
            "display_name": display_name,
            "pt1": p1,
            "pt2": p2,
            "d_threshold": thresh,
            "type": src_type
        }

        os.makedirs(os.path.dirname(self.profile_path), exist_ok=True)
        with open(self.profile_path, "w", encoding="utf-8") as f:
            json.dump(profiles_data, f, indent=4)

    def calibrate_with_opencv(
        self,
        video_source: Union[int, str] = "data/samples/surveillance.avi",
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
        src = normalize_video_source(video_source)
        if isinstance(src, int) and sys.platform.startswith("win"):
            cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(src)

        # Đọc bỏ 3-5 frame đầu để cảm biến camera hoàn tất đo sáng (Warm-up frames)
        if isinstance(src, int):
            for _ in range(5):
                cap.read()

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            print(f"[Calibrator] Không đọc được frame từ nguồn {video_source}! Dùng vạch mặc định hoặc cache.")
            cached = self.load_config(source=src)
            return cached if cached else ((100, 240), (550, 240))

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
            self.save_config(chosen_line, source=src)
            return chosen_line

        # Thử đọc từ config cũ hoặc dùng mặc định
        cached = self.load_config(source=src)
        return cached if cached else default_line
