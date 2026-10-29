"""
Pydantic Schemas for FastAPI Server (Data Transfer Objects)
"""

from typing import List, Tuple, Optional, Union, Any, Dict
from pydantic import BaseModel, Field


class TripwireUpdateDTO(BaseModel):
    pt1: Tuple[int, int] = Field(..., description="Tọa độ điểm A (x1, y1)")
    pt2: Tuple[int, int] = Field(..., description="Tọa độ điểm B (x2, y2)")
    d_threshold: Optional[float] = Field(35.0, description="Khoảng cách vùng đệm an toàn")


class TrackingStatsDTO(BaseModel):
    success: bool = True
    count_in: int
    count_out: int
    inside: int
    active_objects_count: int
    fps: float
    is_night_mode: bool
    mean_luminance: float
    camera_status: Optional[str] = "online"
    active_source: Optional[str] = None
    resolution: Optional[List[int]] = None


class EventDTO(BaseModel):
    timestamp: str
    event_type: str  # "IN" hoặc "OUT"
    object_id: int


class StandardResponseDTO(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class DeviceItemDTO(BaseModel):
    id: Union[int, str] = Field(..., description="Mã định danh hoặc đường dẫn nguồn")
    name: str = Field(..., description="Tên hiển thị trực quan")
    type: str = Field("webcam", description="'webcam' | 'file' | 'rtsp'")
    resolution: List[int] = Field(default_factory=lambda: [640, 480], description="[Width, Height]")
    available: bool = Field(True, description="Khả dụng hay không")


class DeviceListResponseDTO(BaseModel):
    success: bool = True
    active_source: Union[int, str]
    devices: List[DeviceItemDTO]


class DeviceSwitchRequestDTO(BaseModel):
    source: Union[int, str] = Field(..., description="ID thiết bị webcam (0, 1), đường dẫn video hoặc URL RTSP")
