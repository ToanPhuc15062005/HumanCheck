"""
MASTER APPLICATION RUNNER (DISPATCHER)
Hệ Thống Giám Sát Thông Minh & Đếm Người Qua Lại (Pure DIP)
Môn học: Xử lý ảnh - PTIT HCM | TS. Huỳnh Trung Trụ

Cách sử dụng:
  - Chạy Streamlit Demo:       python run.py --mode=demo
  - Chạy FastAPI Uvicorn App:   python run.py --mode=api
  - Chạy Bộ Kiểm Thử (Tests):  python run.py --mode=test
  - Cấu hình Vạch ảo (OpenCV):  python run.py --mode=calibrate --source 0
"""

import argparse
import os
import subprocess
import sys


def run_demo():
    print("[Dispatcher] Khởi chạy Streamlit Demo Dashboard...")
    cmd = [sys.executable, "-m", "streamlit", "run", os.path.join("app", "demo_streamlit", "app.py")]
    subprocess.run(cmd)


def run_api(host="127.0.0.1", port=8000, source=None):
    if source is not None:
        os.environ["SURVEILLANCE_SOURCE"] = str(source)
    print(f"[Dispatcher] Khởi chạy FastAPI / Uvicorn Server tại http://{host}:{port} (Source: {source or 'Default'})...")
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.server_uvicorn.main:app",
        "--host", host,
        "--port", str(port),
        "--reload"
    ]
    subprocess.run(cmd)


def run_test():
    print("[Dispatcher] Khởi chạy bộ kiểm thử tự động (Unit & Integration Tests)...")
    cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]
    subprocess.run(cmd)


def run_calibrate(video_path="data/samples/surveillance.avi"):
    print("[Dispatcher] Khởi chạy công cụ cấu hình vạch ảo OpenCV...")
    from core.module2_tripwire_gui.calibrator import TripwireCalibrator, normalize_video_source
    calibrator = TripwireCalibrator()
    norm_source = normalize_video_source(video_path)
    if isinstance(norm_source, str) and not os.path.exists(norm_source) and os.path.exists("test/surveillance.avi"):
        norm_source = "test/surveillance.avi"
    chosen_line = calibrator.calibrate_with_opencv(norm_source)
    print(f"[Dispatcher] Đã lưu tọa độ vạch ảo: {chosen_line}")


def run_frontend():
    print("[Dispatcher] Khởi chạy React Swiss Luxury Frontend (Vite Dev Server)...")
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    cmd = ["npm", "run", "dev"]
    subprocess.run(cmd, cwd=frontend_dir, shell=True)


def main():
    parser = argparse.ArgumentParser(description="HumanCheck Pure DIP Surveillance System")
    parser.add_argument(
        "--mode",
        choices=["demo", "api", "test", "calibrate", "frontend"],
        default="demo",
        help="Chế độ chạy: 'frontend' (React Swiss Luxury Suite), 'api' (FastAPI/Uvicorn), 'demo' (Streamlit), 'test' (Unit Tests), 'calibrate' (Vẽ vạch)"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host IP cho API")
    parser.add_argument("--port", type=int, default=8000, help="Port cho API")
    parser.add_argument("--source", default="data/samples/surveillance.avi", help="Nguồn video để cấu hình vạch hoặc chạy API")

    args = parser.parse_args()

    if args.mode == "frontend":
        run_frontend()
    elif args.mode == "demo":
        run_demo()
    elif args.mode == "api":
        run_api(args.host, args.port, args.source)
    elif args.mode == "test":
        run_test()
    elif args.mode == "calibrate":
        run_calibrate(args.source)


if __name__ == "__main__":
    main()
