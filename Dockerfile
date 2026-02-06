FROM python:3.12-slim-bookworm

LABEL maintainer="turnstile-solver"
LABEL description="Cloudflare Turnstile Solver with Camoufox"

# 安装系统依赖 (Camoufox/Firefox 需要的库)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 基础工具
    wget \
    curl \
    # X11 和显示相关
    xvfb \
    x11-utils \
    # Firefox/GTK 依赖
    libgtk-3-0 \
    libdbus-glib-1-2 \
    libxt6 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libnspr4 \
    libnss3 \
    # 字体
    fonts-liberation \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 下载 Camoufox 浏览器
RUN python -m camoufox fetch

# 复制应用代码
COPY api_solver.py .
COPY db_results.py .
COPY browser_configs.py .

# 设置环境变量
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1
ENV API_KEY=""

# 暴露端口
EXPOSE 5072

# 启动脚本
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
