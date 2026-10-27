"""
MODULE 3: KHỬ BÓNG ĐỔ VÀ KHỬ NHIỄU RUNG LẮC MÔI TRƯỜNG (SHADOW & NOISE FILTER)
Môn học: Xử lý ảnh (Digital Image Processing) - PTIT HCM
Giảng viên phụ trách: TS. Huỳnh Trung Trụ
Slide 5 (Color & Shadow), Slide 7 (Morphological Operations)
"""

import cv2
import numpy as np


class ShadowAndNoiseFilter:
    """
    Bộ xử lý hình thái học và khử bóng đổ:
    1. Shadow Removal: Cắt ngưỡng nhị phân > 250 để loại bỏ hoàn toàn pixel bóng xám 127 của MOG2.
    2. Morphological Opening: (A o B) = (A (-) B) (+) B với kernel 5x5 để xóa nhiễu hạt, lá cây, vi chuyển động.
    3. Morphological Closing: (A . B) = (A (+) B) (-) B để hàn kín các lỗ hổng bên trong thân người.
    """

    def __init__(self, kernel_size: int = 5):
        self.kernel_size = kernel_size
        self.kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))

    def clean_mask(self, raw_mask: np.ndarray, remove_shadows: bool = True) -> np.ndarray:
        """
        Làm sạch mặt nạ tiền cảnh thô.

        Args:
            raw_mask (np.ndarray): Mặt nạ thô từ MOG2 (chứa 0, 127, 255).
            remove_shadows (bool): Nếu True, loại bỏ pixel bóng đổ 127.

        Returns:
            np.ndarray: Mặt nạ nhị phân sạch (chỉ gồm 0 và 255).
        """
        if raw_mask is None or raw_mask.size == 0:
            return np.zeros((100, 100), dtype=np.uint8)

        if remove_shadows:
            # Ngưỡng 250 để cắt bóng xám 127, chỉ giữ lại tiền cảnh thực sự 255
            _, mask_thresh = cv2.threshold(raw_mask, 250, 255, cv2.THRESH_BINARY)
        else:
            _, mask_thresh = cv2.threshold(raw_mask, 100, 255, cv2.THRESH_BINARY)

        # 1. Morphological Opening: Loại bỏ rung lắc vi chuyển động
        mask_opened = cv2.morphologyEx(mask_thresh, cv2.MORPH_OPEN, self.kernel, iterations=1)

        # 2. Morphological Closing: Hàn kín khoảng trống thân người
        mask_closed = cv2.morphologyEx(mask_opened, cv2.MORPH_CLOSE, self.kernel, iterations=2)

        return mask_closed
