FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    libopenblas-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 基于新的构建上下文调整路径
COPY knowledge_storm ./knowledge_storm
COPY setup.py .
COPY requirements.txt .
COPY README.md .
COPY examples/costorm_examples/app.py .

RUN pip install --no-cache-dir \
    -r requirements.txt \
    lxml[html_clean]==5.2.1 \
    flask==3.0.3 \
    flask-sqlalchemy==3.1.1 \
    flask-migrate==4.0.5 \
    flask-cors==4.0.0 \
    flask-socketio==5.3.6 \
    eventlet==0.33.3 \
    pyjwt==2.8.0 \
    gunicorn==21.2.0 \
    greenlet==3.0.3 \
    psycopg2-binary==2.9.9 \
    -e .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]