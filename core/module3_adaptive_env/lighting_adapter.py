"""
MODULE 3: THÍCH ỨNG ÁNH SÁNG & XỬ LÝ THIẾU SÁNG BAN ĐÊM (LIGHTING ADAPTER)
Môn học: Xử lý ảnh (Digital Image Processing) - PTIT HCM
Giảng viên phụ trách: TS. Huỳnh Trung Trụ
Slide 2 (Point Operations), Slide 4 (Histograms), Slide 5 (Color Models)
"""

from typing import Tuple
import cv2
import numpy as np


class LightingAdapter:
    """
    Bộ thích ứng độ sáng tự động:
    - Đo độ chói trung bình trên không gian màu HSV (kênh V).
    - Tính toán hệ số Gamma thích ứng nếu môi trường thiếu sáng (V < night_threshold).
    - Áp dụng Gamma Correction qua bảng Lookup Table (LUT) tốc độ cao.
    - Cân bằng tương phản cục bộ thích nghi CLAHE trên kênh V để giữ sắc nét biên dáng người.
    """

    def __init__(
        self,
        night_threshold: float = 75.0,
        gamma_min: float = 0.35,
        gamma_slope: float = 0.55,
        clahe_clip_limit: float = 2.0,
        clahe_grid_size: Tuple[int, int] = (8, 8)
    ):
        self.night_threshold = night_threshold
        self.gamma_min = gamma_min
        self.gamma_slope = gamma_slope
        self.clahe = cv2.createCLAHE(clipLimit=clahe_clip_limit, tileGridSize=clahe_grid_size)

    def process(self, frame: np.ndarray) -> Tuple[np.ndarray, bool, float, float]:
        """
        Xử lý kéo sáng thích ứng trên khung hình.

        Args:
            frame (np.ndarray): Khung hình BGR gốc.

        Returns:
            Tuple[np.ndarray, bool, float, float]:
                - frame_enhanced: Ảnh sau xử lý
                - is_night_mode: True nếu kích hoạt chế độ ban đêm
                - mean_lum: Độ sáng trung bình kênh V
                - gamma_val: Giá trị gamma áp dụng
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        mean_lum = float(np.mean(v))

        if mean_lum < self.night_threshold:
            # Thiếu sáng -> Tính Gamma thích nghi (gamma < 1.0 kéo sáng)
            gamma_val = self.gamma_min + self.gamma_slope * (mean_lum / self.night_threshold)
            gamma_val = max(0.2, min(1.0, gamma_val))

            # Bảng LUT 256 giá trị để tăng tốc tối đa
            table = np.array([((i / 255.0) ** gamma_val) * 255.0 for i in range(256)]).astype("uint8")
            v_gamma = cv2.LUT(v, table)
            v_enhanced = self.clahe.apply(v_gamma)

            frame_enhanced = cv2.cvtColor(cv2.merge([h, s, v_enhanced]), cv2.COLOR_HSV2BGR)
            return frame_enhanced, True, mean_lum, gamma_val

        return frame.copy(), False, mean_lum, 1.0
