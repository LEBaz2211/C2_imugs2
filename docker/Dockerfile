FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md /app/
COPY src /app/src
COPY fixtures /app/fixtures
COPY schemas /app/schemas
COPY docs /app/docs
COPY docker-compose.yml docker-compose.legacy-ros.yml /app/
COPY frontend/src /app/frontend/src
COPY legacy_ros/config /app/legacy_ros/config
COPY legacy_ros/fog /app/legacy_ros/fog
COPY legacy_ros/edge /app/legacy_ros/edge

RUN pip install --no-cache-dir -e .

CMD ["c2-imugs2-api"]
