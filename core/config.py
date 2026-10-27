"""
Core Configuration Module for HumanCheck System.
Defines Pydantic models and dataclasses for thresholds and system parameters.
"""

from typing import Tuple
from pydantic import BaseModel, Field


class DetectionConfig(BaseModel):
    """Cấu hình cho bộ phân đoạn và lọc hình học dáng người (Module 1)."""
    min_area: float = Field(default=400.0, description="Diện tích tối thiểu (pixel) để loại bỏ nhiễu rung lắc")
    min_aspect_ratio: float = Field(default=0.85, description="Tỷ lệ H/W tối thiểu đại diện cho dáng người đứng")
    max_aspect_ratio: float = Field(default=4.5, description="Tỷ lệ H/W tối đa để lọc vệt dị thường")
    override_large_area: float = Field(default=1200.0, description="Ngưỡng diện tích lớn bỏ qua kiểm tra tỷ lệ")
    use_moments: bool = Field(default=True, description="Tính tâm bằng Spatial Moments")


class TrackerConfig(BaseModel):
    """Cấu hình cho bộ theo dõi tâm (Centroid Tracker)."""
    max_disappeared: int = Field(default=15, description="Số frame tối đa trước khi hủy đăng ký đối tượng")
    max_distance: float = Field(default=60.0, description="Khoảng cách Euclidean tối đa để ghép cặp tâm")
    max_history: int = Field(default=40, description="Số điểm tâm lưu trữ trong vệt quỹ đạo")


class TripwireConfig(BaseModel):
    """Cấu hình cho vạch ảo và vùng đệm an toàn (Module 2)."""
    line_coords: Tuple[Tuple[int, int], Tuple[int, int]] = Field(
        default=((135, 38), (135, 213)),
        description="Tọa độ 2 điểm định nghĩa vạch ảo ((x1, y1), (x2, y2))"
    )
    d_threshold: float = Field(default=35.0, description="Khoảng cách vùng đệm an toàn Hysteresis (pixel)")


class AdaptiveEnvConfig(BaseModel):
    """Cấu hình cho bộ thích ứng môi trường (Module 3)."""
    enable_night_mode: bool = Field(default=True, description="Tự động kích hoạt Gamma + CLAHE khi thiếu sáng")
    night_lux_threshold: float = Field(default=75.0, description="Ngưỡng độ sáng trung bình kênh V để bật chế độ đêm")
    enable_shock_reset: bool = Field(default=True, description="Reset background ngay khi bật/tắt đèn đột ngột")
    shock_white_ratio: float = Field(default=0.70, description="Tỷ lệ diện tích trắng trên mask để nhận diện đổi sáng")
    enable_shadow_removal: bool = Field(default=True, description="Lọc bỏ pixel bóng xám 127")
    morph_kernel_size: int = Field(default=5, description="Kích thước ma trận cấu trúc Morphological Opening/Closing")


class SystemConfig(BaseModel):
    """Cấu hình toàn diện cho toàn bộ hệ thống HumanCheck."""
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    tracker: TrackerConfig = Field(default_factory=TrackerConfig)
    tripwire: TripwireConfig = Field(default_factory=TripwireConfig)
    adaptive_env: AdaptiveEnvConfig = Field(default_factory=AdaptiveEnvConfig)
    video_source: str = Field(default="data/samples/surveillance.avi", description="Đường dẫn video hoặc camera index")
