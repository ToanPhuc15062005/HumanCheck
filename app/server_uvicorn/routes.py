"""
FastAPI Routes for Video Streaming, Realtime Stats and Tripwire Config
"""

import asyncio
import json
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.server_uvicorn.service import VideoSurveillanceService
from app.server_uvicorn.schemas import TripwireUpdateDTO, TrackingStatsDTO, StandardResponseDTO

router = APIRouter()
service = VideoSurveillanceService.get_instance()


def mjpeg_frame_generator(use_mask: bool = False):
    """Generator sinh chuỗi frames định dạng MJPEG cho browser."""
    while True:
        jpeg_bytes = service.get_latest_frame_jpeg(use_mask=use_mask)
        if jpeg_bytes is not None:
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + jpeg_bytes + b"\r\n")
        time.sleep(0.033)


@router.get("/health", response_model=StandardResponseDTO)
async def health_check():
    return StandardResponseDTO(success=True, message="HumanCheck Pure DIP Surveillance Engine is Running.")


@router.get("/api/v1/stats", response_model=TrackingStatsDTO)
async def get_stats():
    stats = service.get_stats()
    return TrackingStatsDTO(
        success=True,
        count_in=stats["count_in"],
        count_out=stats["count_out"],
        inside=stats["inside"],
        active_objects_count=stats["active_objects_count"],
        fps=stats["fps"],
        is_night_mode=stats["is_night_mode"],
        mean_luminance=stats["mean_luminance"]
    )


@router.get("/api/v1/config")
async def get_config():
    return service.get_config()


@router.get("/api/v1/events")
async def get_events():
    return service.get_events()


@router.post("/api/v1/config/tripwire", response_model=StandardResponseDTO)
async def update_tripwire(config: TripwireUpdateDTO):
    service.update_tripwire(config.pt1, config.pt2, config.d_threshold or 35.0)
    return StandardResponseDTO(
        success=True,
        message="Cập nhật tọa độ vạch ảo thành công",
        data={"pt1": config.pt1, "pt2": config.pt2, "d_threshold": config.d_threshold}
    )


@router.post("/api/v1/stream/play", response_model=StandardResponseDTO)
async def play_stream():
    service.resume()
    return StandardResponseDTO(success=True, message="Đã tiếp tục luồng video", data={"is_paused": False})


@router.post("/api/v1/stream/pause", response_model=StandardResponseDTO)
async def pause_stream():
    service.pause()
    return StandardResponseDTO(success=True, message="Đã tạm dừng luồng video", data={"is_paused": True})


@router.post("/api/v1/stream/toggle", response_model=StandardResponseDTO)
async def toggle_stream():
    is_paused = service.toggle_playback()
    msg = "Đã tạm dừng luồng video" if is_paused else "Đã tiếp tục luồng video"
    return StandardResponseDTO(success=True, message=msg, data={"is_paused": is_paused})


@router.post("/api/v1/reset", response_model=StandardResponseDTO)
async def reset_counters():
    service.reset_counters()
    return StandardResponseDTO(success=True, message="Đã đặt lại bộ đếm IN/OUT và tracker")


@router.get("/api/v1/stream/video")
async def stream_annotated_video():
    """Xem trực tiếp luồng video đã vẽ Bounding Box, Badge và HUD qua trình duyệt."""
    return StreamingResponse(
        mjpeg_frame_generator(use_mask=False),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/api/v1/stream/mask")
async def stream_clean_mask():
    """Xem trực tiếp luồng mặt nạ tiền cảnh sạch (Clean Mask) qua trình duyệt."""
    return StreamingResponse(
        mjpeg_frame_generator(use_mask=True),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.websocket("/ws/stats")
async def websocket_stats(websocket: WebSocket):
    """WebSocket stream phát thông số đếm người và telemetry thời gian thực."""
    await websocket.accept()
    try:
        while True:
            stats = service.get_stats()
            await websocket.send_text(json.dumps(stats))
            await asyncio.sleep(0.1)  # 10 Hz telemetry push
    except WebSocketDisconnect:
        pass
