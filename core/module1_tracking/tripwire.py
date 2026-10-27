"""
MODULE 1: MÁY TRẠNG THÁI VÀ ĐẾM NGƯỜI QUA VẠCH ẢO (TRIPWIRE COUNTER)
Môn học: Xử lý ảnh (Digital Image Processing) - PTIT HCM
Giảng viên phụ trách: TS. Huỳnh Trung Trụ
"""

from typing import Dict, Tuple, Optional, Any, List
import numpy as np


class TripwireCounter:
    """
    Bộ đếm người qua vạch ảo kết hợp Máy trạng thái động và Vùng đệm an toàn Hysteresis.
    """

    def __init__(
        self,
        line_coords: Tuple[Tuple[int, int], Tuple[int, int]],
        d_threshold: float = 35.0
    ):
        self.pt1: Tuple[int, int] = (int(line_coords[0][0]), int(line_coords[0][1]))
        self.pt2: Tuple[int, int] = (int(line_coords[1][0]), int(line_coords[1][1]))
        self.d_threshold: float = float(d_threshold)

        self.count_in: int = 0
        self.count_out: int = 0
        self.states: Dict[int, Dict[str, Any]] = {}

        self._calculate_line_geometry()

    def _calculate_line_geometry(self) -> None:
        """Tính toán chiều dài vạch và vector pháp tuyến để dựng vùng đệm an toàn."""
        dx = float(self.pt2[0] - self.pt1[0])
        dy = float(self.pt2[1] - self.pt1[1])
        self.line_len = max(1e-5, np.hypot(dx, dy))

        self.nx = -dy / self.line_len
        self.ny = dx / self.line_len

        self.b_out_p1 = (int(self.pt1[0] + self.nx * self.d_threshold), int(self.pt1[1] + self.ny * self.d_threshold))
        self.b_out_p2 = (int(self.pt2[0] + self.nx * self.d_threshold), int(self.pt2[1] + self.ny * self.d_threshold))
        self.b_in_p1 = (int(self.pt1[0] - self.nx * self.d_threshold), int(self.pt1[1] - self.ny * self.d_threshold))
        self.b_in_p2 = (int(self.pt2[0] - self.nx * self.d_threshold), int(self.pt2[1] - self.ny * self.d_threshold))

    def set_line(self, line_coords: Tuple[Tuple[int, int], Tuple[int, int]], d_threshold: Optional[float] = None) -> None:
        """Cập nhật lại tọa độ vạch phân cách và khoảng cách vùng đệm."""
        self.pt1 = (int(line_coords[0][0]), int(line_coords[0][1]))
        self.pt2 = (int(line_coords[1][0]), int(line_coords[1][1]))
        if d_threshold is not None:
            self.d_threshold = float(d_threshold)
        self._calculate_line_geometry()

    def get_signed_distance(self, point: Tuple[int, int]) -> float:
        """
        Tính khoảng cách trực giao có dấu từ điểm point đến đoạn thẳng pt1-pt2.
        Giá trị > 0: Nằm ở phía OUT_SIDE.
        Giá trị <= 0: Nằm ở phía IN_SIDE.
        """
        px, py = point
        cross = (self.pt2[0] - self.pt1[0]) * (py - self.pt1[1]) - (self.pt2[1] - self.pt1[1]) * (px - self.pt1[0])
        return float(cross / self.line_len)

    def is_within_segment_projection(self, point: Tuple[int, int], margin: float = 0.35) -> bool:
        """
        Kiểm tra hình chiếu của điểm lên phương của vạch có nằm trong phạm vi đoạn thẳng (kèm biên mở rộng).
        """
        px, py = point
        dx = float(self.pt2[0] - self.pt1[0])
        dy = float(self.pt2[1] - self.pt1[1])
        t = ((px - self.pt1[0]) * dx + (py - self.pt1[1]) * dy) / (self.line_len ** 2)
        return (-margin) <= t <= (1.0 + margin)

    def update(self, objects: Dict[int, Tuple[int, int]]) -> Dict[str, Any]:
        """Cập nhật máy trạng thái cho tất cả các đối tượng và tiến hành đếm."""
        active_ids = set(objects.keys())
        for old_id in list(self.states.keys()):
            if old_id not in active_ids:
                del self.states[old_id]

        events: List[Tuple[str, int]] = []

        for obj_id, centroid in objects.items():
            dist = self.get_signed_distance(centroid)
            current_side = "OUT_SIDE" if dist > 0 else "IN_SIDE"

            if obj_id not in self.states:
                self.states[obj_id] = {
                    "direction": current_side,
                    "last_counted": None,
                    "has_reached_safe_zone": False
                }
                if abs(dist) >= self.d_threshold:
                    self.states[obj_id]["has_reached_safe_zone"] = True
                continue

            state = self.states[obj_id]
            prev_side = state["direction"]

            # Kiểm tra vùng đệm an toàn Hysteresis
            if abs(dist) >= self.d_threshold:
                if state["last_counted"] == "IN" and current_side == "IN_SIDE":
                    state["has_reached_safe_zone"] = True
                elif state["last_counted"] == "OUT" and current_side == "OUT_SIDE":
                    state["has_reached_safe_zone"] = True

            # Chuyển trạng thái khi cắt qua vạch (kèm xác thực hình chiếu trong phạm vi đoạn thẳng)
            if prev_side is not None and prev_side != current_side:
                if self.is_within_segment_projection(centroid, margin=0.35):
                    if prev_side == "OUT_SIDE" and current_side == "IN_SIDE":
                        if state["last_counted"] is None or (state["last_counted"] == "OUT" and state["has_reached_safe_zone"]):
                            self.count_in += 1
                            state["last_counted"] = "IN"
                            state["has_reached_safe_zone"] = False
                            events.append(("IN", obj_id))

                    elif prev_side == "IN_SIDE" and current_side == "OUT_SIDE":
                        if state["last_counted"] is None or (state["last_counted"] == "IN" and state["has_reached_safe_zone"]):
                            self.count_out += 1
                            state["last_counted"] = "OUT"
                            state["has_reached_safe_zone"] = False
                            events.append(("OUT", obj_id))

            state["direction"] = current_side

        return {
            "count_in": self.count_in,
            "count_out": self.count_out,
            "inside": max(0, self.count_in - self.count_out),
            "events": events,
            "states": self.states
        }

    @property
    def inside(self) -> int:
        return max(0, self.count_in - self.count_out)

    def reset(self) -> None:
        self.count_in = 0
        self.count_out = 0
        self.states.clear()
