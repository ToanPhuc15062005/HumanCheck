"""
MODULE 3: BỘ TRỪ NỀN THÍCH NGHI & ĐỒNG HÓA HẬU CẢNH (BACKGROUND ENGINE)
Môn học: Xử lý ảnh (Digital Image Processing) - PTIT HCM
Giảng viên phụ trách: TS. Huỳnh Trung Trụ
Slide 3 (Combining Images), Cơ chế Background Absorption & Fast Illumination Shock Reset
"""

from typing import Tuple
import cv2
import numpy as np


class BackgroundEngine:
    """
    Bộ trừ nền MOG2 nâng cao:
    1. Cập nhật nền thích nghi liên tục theo thời gian: B_t = alpha * B_{t-1} + (1 - alpha) * I_t
    2. Cơ chế Fast Background Reset: Khi tỷ lệ pixel trắng > shock_white_ratio (bật/tắt đèn đột ngột),
       cập nhật nóng với learningRate = 1.0 để làm sạch nền ngay trong frame kế tiếp.
    3. Hỗ trợ phát hiện bóng đổ (detectShadows = True, gán pixel bóng thành 127).
    """

    def __init__(
        self,
        history: int = 500,
        var_threshold: float = 25.0,
        detect_shadows: bool = True,
        shock_white_ratio: float = 0.70
    ):
        self.history = history
        self.var_threshold = var_threshold
        self.detect_shadows = detect_shadows
        self.shock_white_ratio = shock_white_ratio

        self.subtractor = cv2.createBackgroundSubtractorMOG2(
            history=self.history,
            varThreshold=self.var_threshold,
            detectShadows=self.detect_shadows
        )

    def apply(self, frame: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Trừ nền và phát hiện hiện tượng đổi sáng toàn cảnh.

        Args:
            frame (np.ndarray): Khung hình BGR (hoặc sau khi đã cân bằng sáng).

        Returns:
            Tuple[np.ndarray, bool]:
                - fg_mask: Mặt nạ tiền cảnh thô (0, 127 cho bóng, 255 cho chuyển động).
                - shock_detected: True nếu phát hiện đổi sáng đột ngột (đã reset nền).
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        fg_mask = self.subtractor.apply(blurred)

        # Kiểm tra tỷ lệ pixel trắng
        total_pixels = float(frame.shape[0] * frame.shape[1])
        white_pixels = float(np.count_nonzero(fg_mask == 255))
        ratio = white_pixels / max(1.0, total_pixels)

        if ratio > self.shock_white_ratio:
            # Hiện tượng bật/tắt đèn đột ngột -> Reset nền ngay tức thì
            self.subtractor.apply(blurred, learningRate=1.0)
            clean_empty_mask = np.zeros_like(gray)
            return clean_empty_mask, True

        return fg_mask, False

    def reset(self) -> None:
        """Xóa trắng mô hình nền."""
        self.subtractor = cv2.createBackgroundSubtractorMOG2(
            history=self.history,
            varThreshold=self.var_threshold,
            detectShadows=self.detect_shadows
        )
