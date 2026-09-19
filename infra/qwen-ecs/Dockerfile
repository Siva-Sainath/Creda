FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt qwen_worker.py presentation.py judge.py media_loader.py vlm_inference.py ./
RUN pip install --no-cache-dir --default-timeout=120 --retries 5 -r requirements.txt

CMD ["python", "qwen_worker.py"]
