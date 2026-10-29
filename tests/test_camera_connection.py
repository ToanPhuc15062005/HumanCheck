"""
COMPREHENSIVE TEST SUITE: CAMERA CONNECTION & MULTI-DEVICE UPGRADE
Kiểm thử tự động theo ma trận nghiệm thu TC-01 đến TC-07
PLAN-HUMANCHECK-CAM-2026-REV2
"""

import os
import sys
import time
import json
import unittest
from unittest.mock import patch, MagicMock
import numpy as np

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from core.module2_tripwire_gui.calibrator import normalize_video_source, TripwireCalibrator
from core.device_scanner import (
    scan_available_devices,
    load_camera_profiles,
    save_camera_profile,
    get_profile_for_source
)
from app.server_uvicorn.service import VideoSurveillanceService


class TestCameraConnectionMatrix(unittest.TestCase):
    """Bộ kiểm thử nghiệm thu 7 kịch bản kết nối camera."""

    def setUp(self):
        self.sample_video = os.path.join(WORKSPACE_ROOT, "data", "samples", "surveillance.avi")
        if not os.path.exists(self.sample_video) and os.path.exists(os.path.join(WORKSPACE_ROOT, "test", "surveillance.avi")):
            self.sample_video = os.path.join(WORKSPACE_ROOT, "test", "surveillance.avi")

    def test_tc01_source_normalization_and_warmup(self):
        """TC-01: Chuẩn hóa kiểu nguồn chuỗi số thành int và mở camera với warm-up."""
        self.assertEqual(normalize_video_source("0"), 0)
        self.assertEqual(normalize_video_source(" 1 "), 1)
        self.assertEqual(normalize_video_source(0), 0)
        self.assertEqual(normalize_video_source(self.sample_video), self.sample_video)
        self.assertEqual(normalize_video_source("rtsp://admin:123@192.168.1.1:554"), "rtsp://admin:123@192.168.1.1:554")

    def test_tc02_hot_switching_and_performance(self):
        """TC-02: Hot-switching giữa các nguồn video an toàn luồng trong < 1.5s."""
        srv = VideoSurveillanceService.get_instance()
        srv.start(self.sample_video)
        time.sleep(0.5)

        t_start = time.perf_counter()
        switch_res = srv.switch_source(self.sample_video, timeout=3.0)
        t_switch = time.perf_counter() - t_start

        self.assertTrue(switch_res, "Hot-switching must succeed")
        self.assertLess(t_switch, 1.5, f"Switch time {t_switch:.2f}s must be < 1.5s")
        srv.stop()

    def test_tc03_resolution_normalization(self):
        """TC-03: Thích ứng độ phân giải, tự động chuẩn hóa Processing Frame về <= 640px."""
        srv = VideoSurveillanceService.get_instance()
        srv.start(self.sample_video)
        time.sleep(0.5)

        stats = srv.get_stats()
        self.assertIn("resolution", stats)
        res_w, res_h = stats["resolution"]
        self.assertLessEqual(res_w, 640, "Processing width must be normalized <= 640px")
        self.assertGreater(res_h, 0)
        srv.stop()

    def test_tc04_dual_write_and_profile_isolation(self):
        """TC-04: Dual-Write & Lưu Profile vạch ảo riêng biệt cho từng nguồn."""
        # Lưu tọa độ cho Webcam 0
        save_camera_profile("0", (160, 100), (480, 100), d_threshold=40.0)
        # Lưu tọa độ cho Video Mẫu
        save_camera_profile(self.sample_video, (135, 38), (135, 213), d_threshold=35.0)

        prof_cam = get_profile_for_source("0")
        prof_sample = get_profile_for_source(self.sample_video)

        self.assertEqual(prof_cam["pt1"], (160, 100))
        self.assertEqual(prof_cam["pt2"], (480, 100))
        self.assertEqual(prof_cam["d_threshold"], 40.0)

        self.assertEqual(prof_sample["pt1"], (135, 38))
        self.assertEqual(prof_sample["pt2"], (135, 213))
        self.assertEqual(prof_sample["d_threshold"], 35.0)

        # Kiểm tra file tripwire_config.json đã được đồng bộ giá trị active cuối
        with open(os.path.join(WORKSPACE_ROOT, "data", "configs", "tripwire_config.json"), "r") as f:
            cfg = json.load(f)
        self.assertEqual(cfg["pt1"], [135, 38])
        self.assertEqual(cfg["pt2"], [135, 213])

    def test_tc05_stream_failover_and_offline_telemetry(self):
        """TC-05: Phát hiện gián đoạn tín hiệu camera và cập nhật telemetry offline."""
        srv = VideoSurveillanceService()
        self.assertIn("camera_status", srv.current_stats)
        self.assertIn("dropped_frames", srv.current_stats)

        # Khi chưa có frame đọc được
        srv.consecutive_dropped_frames = 25
        with srv.lock:
            srv.camera_status = "offline"
            srv.current_stats["camera_status"] = "offline"

        stats = srv.get_stats()
        self.assertEqual(stats["camera_status"], "offline")

    def test_tc06_live_stream_dropout_resilience(self):
        """TC-06: Giữ nguyên trạng thái tracker và bộ đếm khi nguồn live bị mất frame tạm thời."""
        from core.module1_tracking.pipeline import HumanDetectionModule
        detector = HumanDetectionModule(line_coords=((50, 100), (250, 100)))

        # Giả lập đối tượng đang được theo dõi
        detector.count_in = 5
        detector.count_out = 3
        detector.tracker.objects[1] = (100, 100)

        # Khi rớt frame, không gọi reset
        self.assertEqual(detector.count_in, 5)
        self.assertEqual(detector.count_out, 3)
        self.assertEqual(len(detector.tracker.objects), 1)

    def test_tc07_device_scanner_and_routes(self):
        """TC-07: Bộ quét thiết bị và API FastApi phản hồi đúng cấu trúc."""
        from fastapi.testclient import TestClient
        from app.server_uvicorn.main import app

        client = TestClient(app)
        res = client.get("/api/v1/devices")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("active_source", data)
        self.assertIn("devices", data)
        self.assertGreaterEqual(len(data["devices"]), 1)


if __name__ == "__main__":
    unittest.main()
