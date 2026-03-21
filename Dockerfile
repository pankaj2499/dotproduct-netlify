FROM python:3.11-slim

WORKDIR /workspace

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JAVA_HOME=/usr/lib/jvm/default-java \
    PATH=/usr/lib/jvm/default-java/bin:$PATH \
    PYSPARK_PYTHON=python \
    SPARK_LOCAL_HOSTNAME=localhost

RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless git \
    && rm -rf /var/lib/apt/lists/*

COPY vendor ./vendor
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY dashboard ./dashboard
COPY scripts ./scripts

RUN mkdir -p /workspace/.data \
    && chmod +x /workspace/scripts/*.sh

ENV PYTHONPATH=/workspace
