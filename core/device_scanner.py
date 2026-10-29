"""
CORE UTILITY: BỘ QUÉT THIẾT BỊ CAMERA & QUẢN LÝ PROFILE ĐA THIẾT BỊ
Hệ Thống Giám Sát Thông Minh & Đếm Người Qua Lại (Pure DIP)
Môn học: Xử lý ảnh - PTIT HCM | TS. Huỳnh Trung Trụ
"""

import json
import os
import sys
from typing import List, Dict, Any, Optional, Union, Tuple
import cv2
from core.module2_tripwire_gui.calibrator import normalize_video_source


DEFAULT_PROFILE_PATH = "data/configs/cameras_profile.json"
DEFAULT_TRIPWIRE_CONFIG_PATH = "data/configs/tripwire_config.json"
DEFAULT_SAMPLE_VIDEO_PATH = "data/samples/surveillance.avi"


def scan_available_devices(max_devices: int = 4) -> List[Dict[str, Any]]:
    """
    Quét nhanh các cổng webcam phần cứng và kiểm tra video mẫu có sẵn.
    Trả về danh sách metadata thiết bị: id, name, type, resolution, available.
    """
    devices: List[Dict[str, Any]] = []

    # 1. Quét các cổng Webcam phần cứng (0..max_devices-1)
    for idx in range(max_devices):
        try:
            if sys.platform.startswith("win"):
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            else:
                cap = cv2.VideoCapture(idx)

            if cap.isOpened():
                # Thử đọc frame nhanh để chắc chắn thiết bị không bị busy/locked
                ret, frame = cap.read()
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()

                if ret and frame is not None and w > 0 and h > 0:
                    devices.append({
                        "id": idx,
                        "name": f"Webcam Cổng {idx}",
                        "type": "webcam",
                        "resolution": [w, h],
                        "available": True
                    })
                elif w > 0 and h > 0:
                    # Thiết bị mở được nhưng chưa có frame
                    devices.append({
                        "id": idx,
                        "name": f"Webcam Cổng {idx}",
                        "type": "webcam",
                        "resolution": [w, h],
                        "available": True
                    })
            else:
                cap.release()
        except Exception as e:
            print(f"[DeviceScanner] Lỗi thăm dò cổng {idx}: {e}")

    # 2. Kiểm tra Video Mẫu cục bộ
    sample_path = DEFAULT_SAMPLE_VIDEO_PATH
    if not os.path.exists(sample_path) and os.path.exists("test/surveillance.avi"):
        sample_path = "test/surveillance.avi"

    if os.path.exists(sample_path):
        w, h = 320, 240
        try:
            vcap = cv2.VideoCapture(sample_path)
            if vcap.isOpened():
                vw = int(vcap.get(cv2.CAP_PROP_FRAME_WIDTH))
                vh = int(vcap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                if vw > 0 and vh > 0:
                    w, h = vw, vh
                vcap.release()
        except Exception:
            pass

        devices.append({
            "id": sample_path,
            "name": f"Video Mẫu ({os.path.basename(sample_path)})",
            "type": "file",
            "resolution": [w, h],
            "available": True
        })

    return devices


def load_camera_profiles(profile_path: str = DEFAULT_PROFILE_PATH) -> Dict[str, Any]:
    """Tải toàn bộ cấu hình profile từ file cameras_profile.json."""
    if os.path.exists(profile_path):
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[DeviceScanner] Không thể đọc profiles: {e}")

    # Cấu trúc mặc định nếu file chưa tồn tại
    return {
        "active_source": DEFAULT_SAMPLE_VIDEO_PATH,
        "profiles": {
            DEFAULT_SAMPLE_VIDEO_PATH: {
                "display_name": "Video Giám Sát Mẫu",
                "pt1": [135, 38],
                "pt2": [135, 213],
                "d_threshold": 35.0,
                "type": "file"
            },
            "0": {
                "display_name": "Webcam Mặc Định (Cổng 0)",
                "pt1": [160, 100],
                "pt2": [480, 100],
                "d_threshold": 35.0,
                "type": "webcam"
            },
            "rtsp://default": {
                "display_name": "IP Camera Hành Lang",
                "pt1": [200, 300],
                "pt2": [800, 300],
                "d_threshold": 40.0,
                "type": "rtsp"
            }
        }
    }


def save_camera_profile(
    source: Union[int, str],
    pt1: Tuple[int, int],
    pt2: Tuple[int, int],
    d_threshold: float = 35.0,
    display_name: Optional[str] = None,
    profile_path: str = DEFAULT_PROFILE_PATH,
    tripwire_config_path: str = DEFAULT_TRIPWIRE_CONFIG_PATH
) -> None:
    """
    Cơ chế Dual-Write: Lưu cấu hình profile cho nguồn cụ thể và đồng thời
    cập nhật file cấu hình hoạt động tripwire_config.json.
    """
    src_key = str(normalize_video_source(source))
    p1 = [int(pt1[0]), int(pt1[1])]
    p2 = [int(pt2[0]), int(pt2[1])]
    thresh = float(d_threshold)

    # Xác định loại nguồn
    if isinstance(source, int) or (isinstance(source, str) and source.isdigit()):
        src_type = "webcam"
        default_name = f"Webcam Cổng {source}"
    elif str(source).startswith(("rtsp://", "http://", "https://")):
        src_type = "rtsp"
        default_name = "IP Camera Stream"
    else:
        src_type = "file"
        default_name = os.path.basename(str(source))

    name = display_name or default_name

    # 1. Cập nhật cameras_profile.json
    data = load_camera_profiles(profile_path)
    data["active_source"] = src_key
    if "profiles" not in data:
        data["profiles"] = {}

    data["profiles"][src_key] = {
        "display_name": name,
        "pt1": p1,
        "pt2": p2,
        "d_threshold": thresh,
        "type": src_type
    }

    os.makedirs(os.path.dirname(profile_path), exist_ok=True)
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    # 2. Cập nhật tripwire_config.json (Dual-Write)
    os.makedirs(os.path.dirname(tripwire_config_path), exist_ok=True)
    with open(tripwire_config_path, "w", encoding="utf-8") as f:
        json.dump({
            "pt1": p1,
            "pt2": p2,
            "d_threshold": thresh
        }, f, indent=4)


def get_profile_for_source(
    source: Union[int, str],
    profile_path: str = DEFAULT_PROFILE_PATH,
    tripwire_config_path: str = DEFAULT_TRIPWIRE_CONFIG_PATH,
    frame_resolution: Optional[Tuple[int, int]] = None
) -> Dict[str, Any]:
    """
    Lấy cấu hình vạch ảo theo thứ tự ưu tiên:
    1. Profile khớp chính xác trong cameras_profile.json.
    2. Cấu hình hiện thời trong tripwire_config.json.
    3. Tọa độ mặc định nội suy theo tỷ lệ độ phân giải khung hình.
    """
    src_key = str(normalize_video_source(source))

    # 1. Tìm trong cameras_profile.json
    profiles_data = load_camera_profiles(profile_path)
    if src_key in profiles_data.get("profiles", {}):
        prof = profiles_data["profiles"][src_key]
        return {
            "pt1": tuple(prof["pt1"]),
            "pt2": tuple(prof["pt2"]),
            "d_threshold": float(prof.get("d_threshold", 35.0)),
            "display_name": prof.get("display_name", src_key),
            "type": prof.get("type", "unknown")
        }

    # 2. Đọc từ tripwire_config.json
    if os.path.exists(tripwire_config_path):
        try:
            with open(tripwire_config_path, "r", encoding="utf-8") as f:
                cdata = json.load(f)
                return {
                    "pt1": tuple(cdata["pt1"]),
                    "pt2": tuple(cdata["pt2"]),
                    "d_threshold": float(cdata.get("d_threshold", 35.0)),
                    "display_name": src_key,
                    "type": "custom"
                }
        except Exception:
            pass

    # 3. Mặc định theo resolution
    if frame_resolution and frame_resolution[0] > 0 and frame_resolution[1] > 0:
        w, h = frame_resolution
        return {
            "pt1": (int(w * 0.15), int(h * 0.5)),
            "pt2": (int(w * 0.85), int(h * 0.5)),
            "d_threshold": 35.0,
            "display_name": src_key,
            "type": "default"
        }

    return {
        "pt1": (135, 38),
        "pt2": (135, 213),
        "d_threshold": 35.0,
        "display_name": src_key,
        "type": "default"
    }
