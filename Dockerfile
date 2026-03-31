FROM python:3.12-slim

# The slim image is based on Debian, so we use apt-get to install curl.
# We also install 'ca-certificates' to ensure SSL/TLS connections work correctly.
# The 'rm -rf /var/lib/apt/lists/*' command cleans up apt cache to keep the image size minimal.
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
COPY vendor/ibapi ./vendor/ibapi
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir --no-build-isolation -r requirements.txt

COPY . .

# Launch FastAPI app with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
