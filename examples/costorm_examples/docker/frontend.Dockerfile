FROM python:3.10-slim

# 安装必要系统依赖
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 仅复制前端必要文件
COPY ../../../examples/costorm_examples/streamlit_app.py .
COPY ../../../examples/costorm_examples/.config ./config

# 安装直接依赖
RUN pip install --no-cache-dir \
    streamlit==1.32.0 \
    requests==2.32.3 \
    python-dateutil==2.9.0.post0

# 配置环境变量
ENV BASE_API=http://backend:5000/api
ENV STREAMLIT_SERVER_HEADLESS=true

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0"]