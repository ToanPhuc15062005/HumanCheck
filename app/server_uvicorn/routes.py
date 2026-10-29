"""
FastAPI Routes for Video Streaming, Realtime Stats, Tripwire Config and Device Management
"""

import asyncio
import json
import time
from typing import List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.server_uvicorn.service import VideoSurveillanceService
from app.server_uvicorn.schemas import (
    TripwireUpdateDTO,
    TrackingStatsDTO,
    StandardResponseDTO,
    DeviceListResponseDTO,
    DeviceSwitchRequestDTO,
    DeviceItemDTO
)
from core.device_scanner import scan_available_devices, load_camera_profiles

router = APIRouter()
service = VideoSurveillanceService.get_instance()

# Cached devices list to allow instant GET response
_cached_devices: List[Dict[str, Any]] = []


def _get_combined_devices() -> List[Dict[str, Any]]:
    global _cached_devices
    if not _cached_devices:
        _cached_devices = scan_available_devices(max_devices=4)

    # Nạp thêm các nguồn đặc biệt từ camera profiles nếu chưa có
    profiles_data = load_camera_profiles()
    existing_ids = {str(d["id"]) for d in _cached_devices}

    combined = list(_cached_devices)
    for src_id, prof in profiles_data.get("profiles", {}).items():
        if src_id not in existing_ids:
            combined.append({
                "id": int(src_id) if src_id.isdigit() else src_id,
                "name": prof.get("display_name", src_id),
                "type": prof.get("type", "rtsp" if src_id.startswith(("rtsp://", "http://")) else "file"),
                "resolution": [640, 480],
                "available": True
            })
            existing_ids.add(src_id)

    return combined


def mjpeg_frame_generator(use_mask: bool = False):
    """Generator sinh chuỗi frames định dạng MJPEG cho browser."""
    try:
        while True:
            jpeg_bytes = service.get_latest_frame_jpeg(use_mask=use_mask)
            if jpeg_bytes is not None:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + jpeg_bytes + b"\r\n")
            time.sleep(0.033)
    except (GeneratorExit, asyncio.CancelledError):
        pass


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
        mean_luminance=stats["mean_luminance"],
        camera_status=stats.get("camera_status", "online"),
        active_source=str(stats.get("active_source", "")),
        resolution=stats.get("resolution", [320, 240])
    )


@router.get("/api/v1/config")
async def get_config():
    return service.get_config()


@router.get("/api/v1/events")
async def get_events():
    return service.get_events()


@router.get("/api/v1/devices", response_model=DeviceListResponseDTO)
async def list_devices():
    devices = _get_combined_devices()
    return DeviceListResponseDTO(
        success=True,
        active_source=service.video_source,
        devices=[DeviceItemDTO(**d) for d in devices]
    )


@router.post("/api/v1/devices/scan", response_model=DeviceListResponseDTO)
async def trigger_scan_devices():
    global _cached_devices
    _cached_devices = scan_available_devices(max_devices=4)
    devices = _get_combined_devices()
    return DeviceListResponseDTO(
        success=True,
        active_source=service.video_source,
        devices=[DeviceItemDTO(**d) for d in devices]
    )


@router.post("/api/v1/devices/switch", response_model=StandardResponseDTO)
async def switch_device(req: DeviceSwitchRequestDTO):
    success = service.switch_source(req.source)
    if success:
        return StandardResponseDTO(
            success=True,
            message=f"Đã chuyển sang nguồn {req.source} thành công",
            data={
                "active_source": str(service.video_source),
                "camera_status": service.camera_status,
                "resolution": list(service.resolution)
            }
        )
    else:
        return StandardResponseDTO(
            success=False,
            message=f"Không thể kết nối tới nguồn {req.source}. Đã hoàn tác lại nguồn trước.",
            data={
                "active_source": str(service.video_source),
                "camera_status": service.camera_status
            }
        )


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
