FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (with Tsinghua mirror)
COPY app/requirements.txt .
# 修复 Tailscale DNS 无法解析外部域名的问题
RUN printf 'nameserver 223.5.5.5\nnameserver 8.8.8.8\n' > /etc/resolv.conf && pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# Copy application code
COPY app/ .

# Create upload directory
RUN mkdir -p /data/files

EXPOSE 8081

CMD ["uvicorn", "run:app", "--host", "0.0.0.0", "--port", "8081"]
