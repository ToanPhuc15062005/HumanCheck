"""
MODULE 1 UNIT & INTEGRATION TEST RUNNER
Kế thừa toàn bộ kịch bản kiểm thử nguyên bản của Module 1.
"""

import os
import sys
import time
import unittest
import cv2
import numpy as np

# Thêm thư mục gốc vào đường dẫn
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from core.module1_tracking import (
    HumanSegmentor,
    CentroidTracker,
    TripwireCounter,
    SurveillanceVisualizer,
    HumanDetectionModule,
)


class TestModule1LegacySuite(unittest.TestCase):

    def test_segmentor(self):
        synth_mask = np.zeros((400, 600), dtype=np.uint8)
        synth_mask[50:60, 50:60] = 255      # 100px: Nhiễu
        synth_mask[50:70, 150:190] = 255    # 800px, H/W=0.5: Nằm ngang
        synth_mask[150:240, 100:130] = 255  # 2700px, H/W=3.0: Dáng người đứng chuẩn
        synth_mask[150:200, 300:350] = 255  # 2500px: Khối chuyển động lớn

        segmentor = HumanSegmentor(min_area=400, min_aspect_ratio=0.85, override_large_area=1200)
        boxes, centroids, areas = segmentor.filter_and_detect(synth_mask)

        self.assertEqual(len(boxes), 2, f"Kỳ vọng 2 boxes, thực tế: {len(boxes)}")
        self.assertTrue(any(b[2] == 30 and b[3] == 90 for b in boxes), "Thiếu dáng người đứng chuẩn")
        self.assertTrue(any(b[2] == 50 and b[3] == 50 for b in boxes), "Thiếu khối chuyển động lớn")

    def test_tracker(self):
        tracker = CentroidTracker(max_disappeared=3, max_distance=50.0)
        frames_data = [
            [(100, 100, 30, 80), (300, 200, 30, 80)],
            [(100, 115, 30, 80), (315, 200, 30, 80)],
            [(100, 130, 30, 80)],
            [(100, 145, 30, 80)],
            [(100, 160, 30, 80)],
            [(100, 175, 30, 80)],
        ]
        for b in frames_data:
            tracker.update(b)

        self.assertIn(0, tracker.objects, "Người A (ID=0) phải còn tồn tại")
        self.assertNotIn(1, tracker.objects, "Người B (ID=1) phải bị xóa sau 4 frame vắng mặt")

    def test_tripwire(self):
        tripwire = TripwireCounter(line_coords=((550, 200), (50, 200)), d_threshold=35.0)

        # 1. OUT -> IN
        tripwire.update({10: (300, 150)})
        r2 = tripwire.update({10: (300, 210)})
        self.assertEqual(r2["count_in"], 1, "Phải đếm IN = 1")

        # 2. Hesitation quanh vạch (|d| < 35px)
        tripwire.update({10: (300, 195)})
        tripwire.update({10: (300, 205)})
        r5 = tripwire.update({10: (300, 190)})
        self.assertEqual(r5["count_in"], 1)
        self.assertEqual(r5["count_out"], 0)

        # 3. Đạt vùng an toàn -> IN -> OUT
        tripwire.update({10: (300, 280)})
        self.assertTrue(tripwire.states[10]["has_reached_safe_zone"], "Cờ vùng an toàn chưa bật")
        r7 = tripwire.update({10: (300, 150)})
        self.assertEqual(r7["count_out"], 1)
        self.assertEqual(r7["inside"], 0)

        # 4. Đa đối tượng di chuyển ngược chiều đồng thời
        tripwire.update({101: (200, 150), 102: (400, 250)})
        r_multi = tripwire.update({101: (200, 250), 102: (400, 150)})
        self.assertEqual(r_multi["count_in"], 2)
        self.assertEqual(r_multi["count_out"], 2)

        # 5. Xóa trạng thái
        tripwire.reset()
        self.assertEqual(tripwire.count_in, 0)
        self.assertEqual(tripwire.count_out, 0)
        self.assertEqual(len(tripwire.states), 0)

    def test_visualizer(self):
        canvas = np.full((480, 640, 3), 40, dtype=np.uint8)
        tracker = CentroidTracker()
        tracker.objects = {0: (200, 200)}
        tracker.boxes = {0: (180, 140, 40, 120)}
        tracker.history = {0: [(200, 180), (200, 200)]}

        tripwire = TripwireCounter(line_coords=((550, 200), (50, 200)), d_threshold=35.0)
        tripwire.states = {0: {"direction": "IN_SIDE", "last_counted": "IN", "has_reached_safe_zone": True}}

        visualizer = SurveillanceVisualizer()
        annotated = visualizer.draw_all(canvas, tracker, tripwire, fps=30.0, extra_status="TEST OK")
        self.assertEqual(annotated.shape, (480, 640, 3), "Khung hình vẽ không đúng kích thước")

    def test_integration(self):
        sample_path = os.path.abspath(os.path.join(WORKSPACE_ROOT, "data", "samples", "surveillance.avi"))
        self.assertTrue(os.path.exists(sample_path), f"Không tìm thấy video {sample_path}")

        cap = cv2.VideoCapture(sample_path)
        self.assertTrue(cap.isOpened(), f"Không mở được video {sample_path}")

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        detector = HumanDetectionModule(
            line_coords=((w - 20, int(h * 0.52)), (20, int(h * 0.52))),
            d_threshold=20.0,
            min_area=250.0,
            min_aspect_ratio=0.75,
            max_distance=70.0
        )

        t0 = time.time()
        frames_run = 0
        for _ in range(total_frames):
            ret, frame = cap.read()
            if not ret:
                break
            frames_run += 1
            detector.process_frame(frame, annotate=True)
        cap.release()

        elapsed = time.time() - t0
        fps = frames_run / max(1e-5, elapsed)
        self.assertGreaterEqual(detector.tripwire.count_out, 1, "Phải đếm được đối tượng người đi ra ngoài!")
        self.assertGreaterEqual(fps, 30.0, "Tốc độ quá thấp")


if __name__ == "__main__":
    unittest.main()
