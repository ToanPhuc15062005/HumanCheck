"""
KIỂM THỬ TỔNG HỢP KIẾN TRÚC PHÂN TẦNG (FULL TEST SUITE)
Kiểm tra tính đúng đắn của toàn bộ 3 Modules cốt lõi và Pipeline tích hợp.
"""

import os
import sys
import unittest
import cv2
import numpy as np

# Thêm thư mục gốc vào PYTHONPATH
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from core.module1_tracking import (
    HumanSegmentor,
    CentroidTracker,
    TripwireCounter,
    SurveillanceVisualizer,
    HumanDetectionModule
)
from core.module2_tripwire_gui import TripwireGeometry
from core.module3_adaptive_env import (
    LightingAdapter,
    BackgroundEngine,
    ShadowAndNoiseFilter,
    AdaptiveEnvironmentEngine
)


class TestHumanCheckArchitecture(unittest.TestCase):

    def test_module1_segmentor(self):
        """Test lọc contour, diện tích, aspect ratio và moments."""
        synth_mask = np.zeros((400, 600), dtype=np.uint8)
        synth_mask[50:60, 50:60] = 255      # 100px: Nhiễu rung lắc (loại bỏ)
        synth_mask[50:70, 150:190] = 255    # 800px, H/W=0.5: Nằm ngang (loại bỏ)
        synth_mask[150:240, 100:130] = 255  # 2700px, H/W=3.0: Dáng người đứng chuẩn (giữ lại)
        synth_mask[150:200, 300:350] = 255  # 2500px: Khối chuyển động lớn vượt override_large_area (giữ lại)

        segmentor = HumanSegmentor(min_area=400, min_aspect_ratio=0.85, override_large_area=1200)
        boxes, centroids, areas = segmentor.filter_and_detect(synth_mask)

        self.assertEqual(len(boxes), 2, "Phải tìm thấy chính xác 2 đối tượng")
        self.assertEqual(len(centroids), 2)
        self.assertEqual(len(areas), 2)

    def test_module1_tracker(self):
        """Test duy trì ID, ma trận Euclidean và hủy đăng ký khi biến mất."""
        tracker = CentroidTracker(max_disappeared=3, max_distance=50.0)
        frames_data = [
            [(100, 100, 30, 80), (300, 200, 30, 80)],
            [(100, 115, 30, 80), (315, 200, 30, 80)],
            [(100, 130, 30, 80)],
            [(100, 145, 30, 80)],
            [(100, 160, 30, 80)],
            [(100, 175, 30, 80)],
        ]
        for rects in frames_data:
            tracker.update(rects)

        self.assertIn(0, tracker.objects, "Người A (ID=0) phải còn tồn tại")
        self.assertNotIn(1, tracker.objects, "Người B (ID=1) phải bị xóa sau 4 frame vắng mặt")

    def test_module1_tripwire_and_hysteresis(self):
        """Test máy trạng thái, vùng đệm an toàn Hysteresis chống đếm trùng."""
        tripwire = TripwireCounter(line_coords=((550, 200), (50, 200)), d_threshold=35.0)

        # 1. OUT -> IN
        tripwire.update({10: (300, 150)})
        r1 = tripwire.update({10: (300, 210)})
        self.assertEqual(r1["count_in"], 1)

        # 2. Chần chừ gần vạch (|d| < 35px) -> Không được đếm thêm
        tripwire.update({10: (300, 195)})
        tripwire.update({10: (300, 205)})
        r2 = tripwire.update({10: (300, 190)})
        self.assertEqual(r2["count_in"], 1)
        self.assertEqual(r2["count_out"], 0)

        # 3. Đi sâu vào vùng an toàn (|d| >= 35px) rồi quay ra -> Đếm OUT thành công
        tripwire.update({10: (300, 280)})
        self.assertTrue(tripwire.states[10]["has_reached_safe_zone"])
        r3 = tripwire.update({10: (300, 150)})
        self.assertEqual(r3["count_out"], 1)
        self.assertEqual(r3["inside"], 0)

    def test_module2_geometry(self):
        """Test giải tích hình học vạch ảo."""
        pt1 = (0, 100)
        pt2 = (100, 100)
        length, nx, ny = TripwireGeometry.compute_normal_vector(pt1, pt2)
        self.assertAlmostEqual(length, 100.0)

        # Điểm nằm phía trên đường ngang (y=50) vs phía dưới (y=150)
        d_out = TripwireGeometry.signed_distance(pt1, pt2, (50, 50))
        d_in = TripwireGeometry.signed_distance(pt1, pt2, (50, 150))
        self.assertTrue((d_out * d_in) < 0, "Hai điểm hai bên vạch phải có khoảng cách trái dấu")

    def test_module3_adaptive_lighting(self):
        """Test kéo sáng thích ứng ban đêm (Gamma + CLAHE)."""
        adapter = LightingAdapter(night_threshold=75.0)
        dark_frame = np.full((100, 100, 3), 30, dtype=np.uint8)
        enhanced, is_night, mean_lum, gamma_val = adapter.process(dark_frame)

        self.assertTrue(is_night, "Phải nhận diện ảnh thiếu sáng")
        self.assertLess(gamma_val, 1.0, "Gamma phải nhỏ hơn 1.0 để kéo sáng")
        self.assertGreater(np.mean(enhanced), np.mean(dark_frame), "Ảnh sau CLAHE/Gamma phải sáng hơn")

    def test_module3_shadow_removal(self):
        """Test loại bỏ bóng xám 127 của MOG2."""
        shadow_filter = ShadowAndNoiseFilter(kernel_size=5)
        raw_mask = np.zeros((100, 100), dtype=np.uint8)
        raw_mask[20:80, 20:80] = 255  # Tiền cảnh
        raw_mask[80:95, 20:80] = 127  # Bóng đổ xám trên sàn

        clean = shadow_filter.clean_mask(raw_mask, remove_shadows=True)
        # Pixel bóng 127 phải bị chuyển hoàn toàn thành 0
        self.assertEqual(np.count_nonzero(clean[80:95, 20:80] == 255), 0)

    def test_unified_pipeline_integration(self):
        """Test tích hợp toàn diện trên file video test."""
        sample_path = os.path.join(WORKSPACE_ROOT, "data", "samples", "surveillance.avi")
        video_path = sample_path if os.path.exists(sample_path) else os.path.join(WORKSPACE_ROOT, "test", "surveillance.avi")
        self.assertTrue(os.path.exists(video_path), "File surveillance.avi phải tồn tại")

        env_engine = AdaptiveEnvironmentEngine()
        detector = HumanDetectionModule(line_coords=((550, 200), (50, 200)))

        cap = cv2.VideoCapture(video_path)
        frame_count = 0
        while cap.isOpened() and frame_count < 100:
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            clean_mask, enhanced, telemetry = env_engine.process(frame)
            res = detector.process_frame(enhanced, clean_mask=clean_mask, annotate=True)
            self.assertIn("count_in", res)
            self.assertIn("count_out", res)
            self.assertIn("annotated_frame", res)
            frame_count += 1
        cap.release()
        self.assertGreater(frame_count, 50, "Phải xử lý thành công ít nhất 50 frames")


if __name__ == "__main__":
    unittest.main()
