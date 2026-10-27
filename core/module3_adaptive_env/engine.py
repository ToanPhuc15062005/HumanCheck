"""
MODULE 3: BỘ ĐIỀU PHỐI THÍCH ỨNG MÔI TRƯỜNG & HẬU CẢNH THÔNG MINH (ADAPTIVE ENVIRONMENT ENGINE)
Môn học: Xử lý ảnh (Digital Image Processing) - PTIT HCM
Giảng viên phụ trách: TS. Huỳnh Trung Trụ
Tích hợp trọn vẹn 5 cơ chế thích ứng:
1. Thiếu sáng ban đêm: Adaptive Gamma Correction + CLAHE.
2. Trừ nền thích nghi: Adaptive Background Subtraction (MOG2).
3. Đổi sáng đột ngột: Fast Background Reset (learningRate = 1.0).
4. Khử bóng đổ: HSV Shadow Removal (cắt pixel 127).
5. Khử rung lắc môi trường: Morphological Opening (5x5).
"""

from typing import Tuple, Dict, Any
import numpy as np

from core.module3_adaptive_env.lighting_adapter import LightingAdapter
from core.module3_adaptive_env.background_engine import BackgroundEngine
from core.module3_adaptive_env.shadow_filter import ShadowAndNoiseFilter


class AdaptiveEnvironmentEngine:
    """
    Hệ thống thích ứng môi trường toàn diện cung cấp Clean Foreground Mask cho Module 1.
    """

    def __init__(
        self,
        night_threshold: float = 75.0,
        enable_night_mode: bool = True,
        shock_white_ratio: float = 0.70,
        enable_shadow_removal: bool = True,
        morph_kernel_size: int = 5
    ):
        self.enable_night_mode = enable_night_mode
        self.enable_shadow_removal = enable_shadow_removal

        self.lighting_adapter = LightingAdapter(night_threshold=night_threshold)
        self.background_engine = BackgroundEngine(shock_white_ratio=shock_white_ratio)
        self.shadow_filter = ShadowAndNoiseFilter(kernel_size=morph_kernel_size)

    def process(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Chu trình xử lý thích ứng môi trường cho 1 khung hình.

        Args:
            frame (np.ndarray): Khung hình BGR từ camera/video.

        Returns:
            Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
                - clean_mask: Mặt nạ tiền cảnh sạch chuẩn bị cho Module 1
                - processed_frame: Khung hình đã qua xử lý ánh sáng (nếu ban đêm)
                - telemetry: Thông số môi trường (độ sáng, gamma, cảnh báo đổi sáng)
        """
        # 1. Đo sáng & Kéo sáng ban đêm (nếu bật)
        if self.enable_night_mode:
            enhanced_frame, is_night_mode, mean_lum, gamma_val = self.lighting_adapter.process(frame)
        else:
            enhanced_frame, is_night_mode, mean_lum, gamma_val = frame.copy(), False, 100.0, 1.0

        # 2. Trừ nền & Phát hiện đổi sáng đột ngột
        raw_mask, shock_detected = self.background_engine.apply(enhanced_frame)

        # 3. Khử bóng đổ và rung lắc vi chuyển động
        clean_mask = self.shadow_filter.clean_mask(
            raw_mask,
            remove_shadows=self.enable_shadow_removal
        )

        telemetry = {
            "mean_luminance": mean_lum,
            "is_night_mode": is_night_mode,
            "gamma_applied": gamma_val,
            "shock_detected": shock_detected
        }

        return clean_mask, enhanced_frame, telemetry

    def reset(self) -> None:
        """Khôi phục lại toàn bộ mô hình nền của Module 3."""
        self.background_engine.reset()
