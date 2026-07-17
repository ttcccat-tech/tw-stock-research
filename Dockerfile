FROM python:3.11-slim

# 安裝 cron + tzdata + curl (健康檢查用)
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    tzdata \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 設定時區為台北
ENV TZ=Asia/Taipei
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 工作目錄
WORKDIR /app

# 複製並安裝 Python 依賴
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼
COPY . /app/

# 確保必要目錄存在 (volume mount 覆蓋時資料不丟)
RUN mkdir -p /app/data /app/price-history /app/logs /app/reports/weekly

# Cron job 設定
COPY crontab /etc/cron.d/quinn
RUN chmod 0644 /etc/cron.d/quinn && crontab /etc/cron.d/quinn

# 啟動腳本 (背景 cron + 前景 Flask)
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# 健康檢查
HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:5050/api/summary || exit 1

EXPOSE 5050

ENTRYPOINT ["/app/docker-entrypoint.sh"]