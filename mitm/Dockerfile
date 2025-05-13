FROM python:3.13-slim
WORKDIR /app
COPY mitm-proxy.py .
RUN pip install --no-cache-dir --upgrade pip
CMD ["python", "mitm-proxy.py"]
