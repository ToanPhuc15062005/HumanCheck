"""
MODULE 1: BỘ THEO DÕI TÂM ĐỐI TƯỢNG (CENTROID TRACKER)
Môn học: Xử lý ảnh (Digital Image Processing) - PTIT HCM
Giảng viên phụ trách: TS. Huỳnh Trung Trụ
"""

from typing import Dict, List, Tuple, Optional
import numpy as np


class CentroidTracker:
    """
    Bộ theo dõi đối tượng dựa trên tâm (Centroid Tracker thuần DIP).
    Sử dụng ma trận khoảng cách Euclidean và thuật toán ghép cặp tối ưu Greedy.
    """

    def __init__(
        self,
        max_disappeared: int = 15,
        max_distance: float = 60.0,
        max_history: int = 40
    ):
        self.next_object_id: int = 0
        self.objects: Dict[int, Tuple[int, int]] = {}
        self.boxes: Dict[int, Tuple[int, int, int, int]] = {}
        self.disappeared: Dict[int, int] = {}
        self.history: Dict[int, List[Tuple[int, int]]] = {}

        self.max_disappeared = max_disappeared
        self.max_distance = max_distance
        self.max_history = max_history

    def register(self, centroid: Tuple[int, int], box: Tuple[int, int, int, int]) -> int:
        """Đăng ký một đối tượng mới với ID tăng dần."""
        obj_id = self.next_object_id
        self.objects[obj_id] = (int(centroid[0]), int(centroid[1]))
        self.boxes[obj_id] = (int(box[0]), int(box[1]), int(box[2]), int(box[3]))
        self.disappeared[obj_id] = 0
        self.history[obj_id] = [(int(centroid[0]), int(centroid[1]))]
        self.next_object_id += 1
        return obj_id

    def deregister(self, object_id: int) -> None:
        """Hủy đăng ký đối tượng khi đã biến mất khỏi khung nhìn."""
        if object_id in self.objects:
            del self.objects[object_id]
        if object_id in self.boxes:
            del self.boxes[object_id]
        if object_id in self.disappeared:
            del self.disappeared[object_id]
        if object_id in self.history:
            del self.history[object_id]

    def update(
        self,
        rects: List[Tuple[int, int, int, int]],
        centroids: Optional[List[Tuple[int, int]]] = None
    ) -> Dict[int, Tuple[int, int]]:
        """Cập nhật vị trí các đối tượng qua khung hình mới."""
        if len(rects) == 0:
            for obj_id in list(self.disappeared.keys()):
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    self.deregister(obj_id)
            return self.objects

        if centroids is not None and len(centroids) == len(rects):
            input_centroids = np.array(centroids, dtype="int")
        else:
            input_centroids = np.zeros((len(rects), 2), dtype="int")
            for i, (x, y, w, h) in enumerate(rects):
                input_centroids[i] = (int(x + w / 2.0), int(y + h / 2.0))

        if len(self.objects) == 0:
            for i in range(len(input_centroids)):
                self.register(tuple(input_centroids[i]), rects[i])
            return self.objects

        object_ids = list(self.objects.keys())
        object_centroids = list(self.objects.values())

        D = np.linalg.norm(np.array(object_centroids)[:, np.newaxis] - input_centroids, axis=2)
        rows = D.min(axis=1).argsort()
        cols = D.argmin(axis=1)[rows]

        used_rows = set()
        used_cols = set()

        for row, col in zip(rows, cols):
            if row in used_rows or col in used_cols:
                continue

            if D[row, col] > self.max_distance:
                continue

            obj_id = object_ids[row]
            new_centroid = (int(input_centroids[col][0]), int(input_centroids[col][1]))
            
            self.objects[obj_id] = new_centroid
            self.boxes[obj_id] = (int(rects[col][0]), int(rects[col][1]), int(rects[col][2]), int(rects[col][3]))
            self.disappeared[obj_id] = 0

            self.history[obj_id].append(new_centroid)
            if len(self.history[obj_id]) > self.max_history:
                self.history[obj_id].pop(0)

            used_rows.add(row)
            used_cols.add(col)

        unused_cols = set(range(len(input_centroids))) - used_cols
        for col in unused_cols:
            self.register(tuple(input_centroids[col]), rects[col])

        unused_rows = set(range(len(object_centroids))) - used_rows
        for row in unused_rows:
            obj_id = object_ids[row]
            self.disappeared[obj_id] += 1
            if self.disappeared[obj_id] > self.max_disappeared:
                self.deregister(obj_id)

        return self.objects

    def reset(self) -> None:
        """Xóa trắng toàn bộ dữ liệu tracker."""
        self.next_object_id = 0
        self.objects.clear()
        self.boxes.clear()
        self.disappeared.clear()
        self.history.clear()
