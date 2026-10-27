"""
FASTAPI & UVICORN SERVER ENTRYPOINT
Hệ thống Camera Giám Sát Thông Minh (PTIT DIP Engine)
Chạy bằng lệnh: uvicorn app.server_uvicorn.main:app --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.server_uvicorn.routes import router
from app.server_uvicorn.service import VideoSurveillanceService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động dịch vụ xử lý video nền
    service = VideoSurveillanceService.get_instance()
    service.start()
    yield
    # Dừng dịch vụ nền khi shutdown server
    service.stop()


app = FastAPI(
    title="HumanCheck Surveillance Server",
    description="Hệ thống giám sát và đếm người qua lại bằng Xử lý ảnh thuần túy (Pure DIP).",
    version="1.0.0",
    lifespan=lifespan
)

# Cấu hình CORS cho phép kết nối từ mọi frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Mount Frontend SPA if built
import os
from fastapi.staticfiles import StaticFiles

frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.server_uvicorn.main:app", host="127.0.0.1", port=8000, reload=False)
