FROM python:3.12-slim

# Instalacja p910nd + utworzenie katalogu lock (jak w looz11/p910nd)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        p910nd \
    && mkdir -p /var/lock/p910nd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# (opcjonalnie) zależności Pythona
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

# watcher p910nd
COPY watch_printer_and_restart.py .

ENV PYTHONUNBUFFERED=1 \
    P910ND_DEVICE=/dev/usb/lp0 \
    P910ND_PORT=0 \
    P910ND_BIDI=0 \
    CHECK_INTERVAL=5 \
    RESTART_DELAY=2

ENTRYPOINT ["python", "watch_printer_and_restart.py"]
