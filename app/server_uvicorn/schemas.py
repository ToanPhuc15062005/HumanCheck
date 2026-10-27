"""
Pydantic Schemas for FastAPI Server (Data Transfer Objects)
"""

from typing import List, Tuple, Optional
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


class EventDTO(BaseModel):
    timestamp: str
    event_type: str  # "IN" hoặc "OUT"
    object_id: int


class StandardResponseDTO(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
