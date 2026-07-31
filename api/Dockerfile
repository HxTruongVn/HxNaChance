# =============================================================================
# Dockerfile — NaChance API (Production)
# =============================================================================
# Build (chạy từ THƯ MỤC GỐC repo, không phải trong api/):
#   docker build -f api/Dockerfile -t photo-master-api .
# Run:
#   docker run --gpus all -p 8000:8000 -v $(pwd)/weights:/app/weights photo-master-api
# =============================================================================

FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# --- Cài system dependencies ---
RUN apt-get update && apt-get install -y \
    python3.10 python3-pip \
    libgl1-mesa-glx libglib2.0-0 \
    libsm6 libxext6 libxrender-dev \
    git wget \
    && rm -rf /var/lib/apt/lists/*

# --- Cài Python packages ---
# FIX: trước đây chỉ COPY + install api_requirements.txt (chỉ có
# fastapi/uvicorn/pydantic) — dòng cài requirements.txt GỐC (torch,
# opencv, mediapipe, rembg...) bị để dạng comment, phải tự tay bỏ
# comment. Build theo file cũ sẽ thiếu sạch dependency AI. Giờ cài cả
# 2 file thật, không còn bước thủ công nào.
COPY requirements.txt api/requirements.txt ./
RUN pip3 install --no-cache-dir -r api/requirements.txt

# --- Copy source ---
# Build context là thư mục gốc repo (xem lệnh build ở trên) nên copy
# được cả code gốc (package photo_engine/, runtime_manager.py, photo_agent.py,
# weights/) lẫn thư mục api/.
COPY . .

# --- Port ---
EXPOSE 8000

# --- Run với Uvicorn worker (1 worker vì engine dùng singleton + lock) ---
# Nếu deploy phía trước có load-balancer, scale bằng nhiều container thay vì nhiều worker.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
