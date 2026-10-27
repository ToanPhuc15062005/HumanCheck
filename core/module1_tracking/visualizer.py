"""
MODULE 1: BỘ TRỰC QUAN HÓA GIÁM SÁT THỜI GIAN THỰC (SURVEILLANCE VISUALIZER)
Môn học: Xử lý ảnh (Digital Image Processing) - PTIT HCM
Giảng viên phụ trách: TS. Huỳnh Trung Trụ
"""

from typing import Dict, Tuple, Optional, Any, List
import cv2
import numpy as np


class SurveillanceVisualizer:
    """
    Bộ vẽ trực quan hóa giao diện giám sát an ninh thông minh cho Module 1.
    """

    COLOR_IN = (0, 255, 128)      # Xanh lá neon: Đã vào trong (IN)
    COLOR_OUT = (0, 140, 255)     # Cam tươi: Đã ra ngoài (OUT)
    COLOR_TRACK = (0, 255, 255)   # Vàng chanh: Đang theo dõi (TRACKING)
    COLOR_TRAIL = (255, 100, 0)   # Xanh dương sáng: Quỹ đạo chuyển động
    COLOR_BUFFER = (180, 180, 0)  # Vàng xám: Vạch đệm an toàn
    COLOR_LINE = (0, 255, 255)    # Vàng: Vạch ảo chính

    def __init__(self):
        pass

    def draw_tripwire(
        self,
        frame: np.ndarray,
        tripwire_counter: Any
    ) -> np.ndarray:
        """Vẽ vạch đếm ảo chính và 2 vạch đệm an toàn (Hysteresis Buffer Lines)."""
        cv2.line(frame, tripwire_counter.b_out_p1, tripwire_counter.b_out_p2, self.COLOR_BUFFER, 1, cv2.LINE_AA)
        cv2.line(frame, tripwire_counter.b_in_p1, tripwire_counter.b_in_p2, self.COLOR_BUFFER, 1, cv2.LINE_AA)
        cv2.line(frame, tripwire_counter.pt1, tripwire_counter.pt2, self.COLOR_LINE, 3, cv2.LINE_AA)

        text_x = min(tripwire_counter.pt1[0], tripwire_counter.pt2[0])
        text_y = min(tripwire_counter.pt1[1], tripwire_counter.pt2[1]) - 6
        label = f"TRIPWIRE (+/- {int(tripwire_counter.d_threshold)}px)"
        cv2.putText(
            frame,
            label,
            (max(6, text_x), max(14, text_y)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.32,
            self.COLOR_LINE,
            1,
            cv2.LINE_AA
        )
        return frame

    def draw_tracked_objects(
        self,
        frame: np.ndarray,
        objects: Dict[int, Tuple[int, int]],
        boxes: Dict[int, Tuple[int, int, int, int]],
        history: Dict[int, List[Tuple[int, int]]],
        states: Dict[int, Dict[str, Any]],
        tripwire_counter: Optional[Any] = None
    ) -> np.ndarray:
        """Vẽ Bounding Box tinh gọn, nhãn nhỏ sắc nét, tâm và quỹ đạo cho tất cả các đối tượng."""
        for obj_id, centroid in objects.items():
            cx, cy = centroid
            state = states.get(obj_id, {"direction": "OUT_SIDE", "last_counted": None, "has_reached_safe_zone": False})
            last_counted = state.get("last_counted")

            if last_counted == "IN":
                box_color = self.COLOR_IN
            elif last_counted == "OUT":
                box_color = self.COLOR_OUT
            else:
                box_color = self.COLOR_TRACK

            box = boxes.get(obj_id)
            if box is not None:
                x, y, w, h = box
                cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 1)

                badge_w = max(36, min(w, 56))
                badge_h = 13
                y_badge_top = max(0, y - badge_h)
                cv2.rectangle(frame, (x, y_badge_top), (x + badge_w, y), (15, 15, 15), -1)
                cv2.rectangle(frame, (x, y_badge_top), (x + badge_w, y), box_color, 1)

                status_label = f"#{obj_id} {last_counted[0]}" if last_counted else f"#{obj_id}"
                cv2.putText(
                    frame,
                    status_label,
                    (x + 3, max(10, y - 3)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.30,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA
                )

            cv2.circle(frame, (cx, cy), 3, (0, 0, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, (cx, cy), 1, (255, 255, 255), -1, cv2.LINE_AA)

            pts = history.get(obj_id, [])
            if len(pts) >= 2:
                pts_arr = np.array(pts, dtype=np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts_arr], False, self.COLOR_TRAIL, 1, cv2.LINE_AA)

        return frame

    def draw_dashboard(
        self,
        frame: np.ndarray,
        count_in: int,
        count_out: int,
        fps: Optional[float] = None,
        extra_status: Optional[str] = None
    ) -> np.ndarray:
        """Vẽ nhãn telemetry tinh gọn (Micro-HUD) ở góc trên, không che khuất hình ảnh."""
        inside_count = max(0, count_in - count_out)
        
        hud_text = f"IN: {count_in} | OUT: {count_out} | INSIDE: {inside_count}"
        if fps is not None:
            hud_text += f" | {fps:.1f} FPS"

        overlay = frame.copy()
        cv2.rectangle(overlay, (6, 6), (220, 24), (10, 12, 15), -1)
        cv2.rectangle(overlay, (6, 6), (220, 24), (60, 65, 75), 1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        cv2.putText(frame, hud_text, (10, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.30, (240, 245, 250), 1, cv2.LINE_AA)
        return frame

    def draw_all(
        self,
        frame: np.ndarray,
        tracker: Any,
        tripwire_counter: Any,
        fps: Optional[float] = None,
        extra_status: Optional[str] = None
    ) -> np.ndarray:
        """Tiện ích vẽ toàn bộ các lớp giao diện lên khung hình."""
        annotated = frame.copy()
        self.draw_tripwire(annotated, tripwire_counter)
        self.draw_tracked_objects(
            annotated,
            tracker.objects,
            tracker.boxes,
            tracker.history,
            tripwire_counter.states,
            tripwire_counter
        )
        self.draw_dashboard(
            annotated,
            tripwire_counter.count_in,
            tripwire_counter.count_out,
            fps,
            extra_status
        )
        return annotated
