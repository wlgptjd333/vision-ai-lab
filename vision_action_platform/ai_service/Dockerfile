FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    YOLO_CONFIG_DIR=/tmp/Ultralytics
WORKDIR /app

# OpenCV 가 쓰는 시스템 라이브러리
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

# CPU 용 PyTorch 먼저 (CUDA 판보다 훨씬 작음). Docker 에서는 CPU 로 추론한다
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
# Pose 가중치가 없으면 이미지 만들 때 한 번 받아 둔다 (실행 중에는 인터넷이 필요 없게)
RUN test -f models/yolo11n-pose.pt || python -c "from ultralytics import YOLO; import shutil; m=YOLO('yolo11n-pose.pt'); shutil.move('yolo11n-pose.pt','models/yolo11n-pose.pt')"

EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
