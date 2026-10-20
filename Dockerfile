FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY product/football/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY product/football /app/product/football
COPY product/watch/media /app/product/watch/media
COPY product/watch/stage /app/product/watch/stage
COPY product/watch/adapters /app/product/watch/adapters
RUN python product/football/scripts/render.py && useradd -u 10001 -m pitchprism && chown -R pitchprism /app
USER pitchprism
EXPOSE 4180
CMD ["python", "-m", "product.football.server", "--host", "0.0.0.0", "--port", "4180"]
