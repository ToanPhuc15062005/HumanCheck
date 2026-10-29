"""
PHASE 2 ARCHITECTURE: MULTI-CAMERA CONCURRENCY SUBSYSTEM
Surveillance Multi Stream Manager: Điều phối và tổng hợp số liệu của N camera chạy song song.
"""

from typing import Dict, Any, List, Optional
from core.multi_camera.camera_worker import CameraWorker


class SurveillanceMultiStreamManager:
    """Quản lý vòng đời và tổng hợp số liệu N camera đồng thời."""

    _instance: Optional["SurveillanceMultiStreamManager"] = None

    @classmethod
    def get_instance(cls) -> "SurveillanceMultiStreamManager":
        if cls._instance is None:
            cls._instance = SurveillanceMultiStreamManager()
        return cls._instance

    def __init__(self):
        self.workers: Dict[str, CameraWorker] = {}

    def register_camera(self, camera_id: str, video_source: Any) -> CameraWorker:
        if camera_id in self.workers:
            self.workers[camera_id].stop()

        worker = CameraWorker(camera_id, video_source)
        self.workers[camera_id] = worker
        worker.start()
        return worker

    def unregister_camera(self, camera_id: str):
        if camera_id in self.workers:
            self.workers[camera_id].stop()
            del self.workers[camera_id]

    def get_worker(self, camera_id: str) -> Optional[CameraWorker]:
        return self.workers.get(str(camera_id))

    def get_aggregated_metrics(self) -> Dict[str, Any]:
        """Tính tổng số lượt IN, OUT và INSIDE trên toàn bộ hệ thống camera."""
        total_in = 0
        total_out = 0
        total_inside = 0
        camera_list = []

        for cid, worker in self.workers.items():
            st = worker.get_stats()
            total_in += st.get("count_in", 0)
            total_out += st.get("count_out", 0)
            total_inside += st.get("inside", 0)
            camera_list.append(st)

        return {
            "total_cameras": len(self.workers),
            "aggregate_count_in": total_in,
            "aggregate_count_out": total_out,
            "aggregate_inside": total_inside,
            "cameras": camera_list
        }

    def stop_all(self):
        for worker in self.workers.values():
            worker.stop()
        self.workers.clear()

