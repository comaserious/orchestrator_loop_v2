FROM python:3.12-slim

WORKDIR /app

# 필수 패키지 설치 (Playwright dependencies 포함)
RUN apt-get update && apt-get install -y \
    curl wget git libnss3 libatk-bridge2.0-0 libx11-xcb1 libxcomposite1 libxdamage1 \
    libxrandr2 libgbm1 libgtk-3-0 libasound2 \
    && rm -rf /var/lib/apt/lists/*

# uv 설치
RUN pip install --no-cache-dir uv

# requirements
COPY requirements.txt .
RUN uv pip install --system --no-cache-dir -r requirements.txt

# playwright 브라우저 설치
RUN playwright install chromium

# FastAPI app
COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]