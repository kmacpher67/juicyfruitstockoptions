# Dockerfile
# FROM python:3.9-slim
# WORKDIR /app
# COPY . .
# RUN pip install -r requirements.txt
# CMD ["python", "option_analyzer_v5.py"]

# created by github ai copilot 2025-08-11
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "your_main_script.py"]