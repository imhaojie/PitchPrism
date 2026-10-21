FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY product/football/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY product/football /app/product/football
COPY product/watch /app/product/watch
COPY product/broadcast-fx /app/product/broadcast-fx
COPY product/web/assets/fonts /app/product/web/assets/fonts
RUN python product/football/scripts/fetch_media.py && useradd -u 10001 -m pitchprism && chown -R pitchprism /app
USER pitchprism
EXPOSE 4180
CMD ["python", "-m", "product.football.server", "--host", "0.0.0.0", "--port", "4180"]
