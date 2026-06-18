FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md /app/
COPY src /app/src
COPY fixtures /app/fixtures
COPY schemas /app/schemas
COPY docs /app/docs
COPY legacy_ros/config/data/map /app/legacy_ros/config/data/map

RUN pip install --no-cache-dir -e .

CMD ["c2-imugs2-api"]
