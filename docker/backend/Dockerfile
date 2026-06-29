FROM python:3.12-slim

ARG REQUIREMENTS_FILE=development.txt

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements /tmp/requirements

RUN pip install --upgrade pip

RUN pip install -r /tmp/requirements/${REQUIREMENTS_FILE}

CMD ["bash"]